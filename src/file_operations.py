"""
Recon – file_operations.py
Delete stale artefacts but never today’s live log file.
"""
import glob
import logging
import os
from datetime import datetime

from .config import DELETE_OLD_FILE_PATTERNS

def delete_old_files(directory: str) -> None:
    today_log = f"application_{datetime.now():%Y-%m-%d}.log"
    for pattern, description in DELETE_OLD_FILE_PATTERNS.items():
        for path in glob.glob(os.path.join(directory, pattern)):
            # never remove today’s live log
            if os.path.basename(path) == today_log:
                continue
            try:
                os.remove(path)
                logging.debug("deleted %s: %s", description, path)
            except (FileNotFoundError, PermissionError):
                pass  # silent – we don’t care

# helpers kept for other modules
def normalize_path(path, base_directory=None):
    path = path.replace("/", os.sep).replace("\\", os.sep)
    if base_directory and not os.path.isabs(path):
        path = os.path.abspath(os.path.join(base_directory, path))
    return os.path.normpath(path)

def is_excluded(path, excluded_paths):
    normal = normalize_path(path)
    return any(normal.startswith(normalize_path(p)) for p in excluded_paths)

def mask_sensitive_data(content: str) -> str:
    """Mask all values in .env files. Every value is treated as sensitive."""
    out = []
    for line in content.splitlines():
        stripped = line.strip()
        # Preserve comments and blank lines as-is
        if not stripped or stripped.startswith("#"):
            out.append(line)
        elif "=" in line:
            k, _ = line.split("=", 1)
            out.append(f"{k}=****")
        else:
            out.append(line)
    return "\n".join(out)

import ast
import re
from pathlib import Path

def fuzzy_find(query: str, root: Path) -> list[Path]:
    """
    Return every path under *root* that matches *query*.
    Matching rules:
        • bare name     → match basename equality   (db)
        • path suffix   → match path.endswith(query) (managers/db)
        • ignore case & slashes vs back-slashes
    Uses os.walk with directory pruning for performance on large trees.
    """
    from .config import DEFAULT_EXCLUDED_DIRECTORIES
    norm = query.strip("/\\")
    pieces = re.split(r"[\\/]", norm)
    pattern = os.sep.join(pieces).lower()

    hits: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune excluded directories in-place
        dirnames[:] = [d for d in dirnames if d.lower() not in DEFAULT_EXCLUDED_DIRECTORIES]

        rel_dir = os.path.relpath(dirpath, root).lower()
        # Check if this directory itself matches
        if rel_dir.endswith(pattern):
            hits.append(Path(dirpath))
        # Check files
        for fname in filenames:
            rel_file = os.path.join(rel_dir, fname).lower()
            if rel_file.endswith(pattern):
                hits.append(Path(dirpath) / fname)
    return hits


def resolve_import_dependencies(entry_path: str) -> list[str]:
    base = Path.cwd()
    entry = Path(entry_path).resolve()
    seen = set()
    to_visit = [entry]

    while to_visit:
        current = to_visit.pop()
        if current in seen or not current.exists() or not current.suffix == ".py":
            continue
        seen.add(current)

        try:
            content = current.read_text(encoding="utf-8")
            node = ast.parse(content)
        except Exception:
            continue

        for stmt in ast.walk(node):
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                names = [alias.name if isinstance(stmt, ast.Import) else stmt.module for alias in stmt.names]
                for name in names:
                    if not name:
                        continue
                    try:
                        # Match project-local imports only
                        parts = name.split(".")
                        rel_path = Path(base, *parts).with_suffix(".py")
                        if rel_path.exists():
                            to_visit.append(rel_path.resolve())
                    except Exception:
                        pass

    return [str(p.relative_to(base)) for p in seen]
