"""
Recon – manifest.py
Extract file identity from any source file and compile into a manifest.

Extraction strategies by file type:
  .py          → module-level docstring via AST
  .md          → YAML frontmatter (--- delimited)
  everything   → leading comment block (detected by extension)
"""

from __future__ import annotations

import ast
import logging
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Union

from .config import (DEFAULT_EXCLUDED_DIRECTORIES, DEFAULT_EXCLUDED_FILES,
                     DEFAULT_EXCLUDED_FILE_PATTERNS, DEFAULT_EXCLUDED_FILE_TYPES,
                     BINARY_EXTENSIONS, normalize_exclusions)
from .directory_tree import generate_directory_tree

# ── comment syntax lookup ───────────────────────────────────────────
# Maps file extensions to (line_prefix, block_open, block_close).
# line_prefix is for single-line comments; block_open/close for multi-line.
# Either may be None if the language doesn't support that style.

_COMMENT_STYLES: dict[str, tuple[str | None, str | None, str | None]] = {
    # hash-style
    ".py":    ("#",  None,    None),
    ".rb":    ("#",  None,    None),
    ".sh":    ("#",  None,    None),
    ".bash":  ("#",  None,    None),
    ".zsh":   ("#",  None,    None),
    ".yml":   ("#",  None,    None),
    ".yaml":  ("#",  None,    None),
    ".toml":  ("#",  None,    None),
    ".pl":    ("#",  None,    None),
    ".r":     ("#",  None,    None),
    ".ps1":   ("#",  None,    None),
    ".dockerfile": ("#", None, None),
    ".tf":    ("#",  None,    None),
    ".cfg":   ("#",  None,    None),
    ".ini":   (";",  None,    None),
    # C-family (line + block)
    ".js":    ("//", "/*",  "*/"),
    ".jsx":   ("//", "/*",  "*/"),
    ".ts":    ("//", "/*",  "*/"),
    ".tsx":   ("//", "/*",  "*/"),
    ".go":    ("//", "/*",  "*/"),
    ".java":  ("//", "/*",  "*/"),
    ".c":     ("//", "/*",  "*/"),
    ".cpp":   ("//", "/*",  "*/"),
    ".h":     ("//", "/*",  "*/"),
    ".hpp":   ("//", "/*",  "*/"),
    ".cs":    ("//", "/*",  "*/"),
    ".swift": ("//", "/*",  "*/"),
    ".kt":    ("//", "/*",  "*/"),
    ".scala": ("//", "/*",  "*/"),
    ".m":     ("//", "/*",  "*/"),  # Objective-C
    ".rs":    ("//", "/*",  "*/"),
    ".zig":   ("//", None,  None),
    ".v":     ("//", "/*",  "*/"),
    # CSS / SCSS
    ".css":   (None, "/*",  "*/"),
    ".scss":  ("//", "/*",  "*/"),
    ".less":  ("//", "/*",  "*/"),
    # HTML / XML
    ".html":  (None, "<!--", "-->"),
    ".htm":   (None, "<!--", "-->"),
    ".xml":   (None, "<!--", "-->"),
    ".svg":   (None, "<!--", "-->"),
    ".vue":   (None, "<!--", "-->"),
    # Lua / SQL / Haskell
    ".lua":   ("--", "--[[", "]]"),
    ".sql":   ("--", "/*",  "*/"),
    ".hs":    ("--", "{-",  "-}"),
    # Lisp-family
    ".lisp":  (";",  None,  None),
    ".clj":   (";",  None,  None),
    ".el":    (";",  None,  None),
    # TeX / MATLAB
    ".tex":   ("%",  None,  None),
    # Erlang / Elixir
    ".erl":   ("%",  None,  None),
    ".ex":    ("#",  None,  None),
    ".exs":   ("#",  None,  None),
}


# ── extractors ──────────────────────────────────────────────────────

def _extract_py_docstring(path: str) -> str | None:
    """Extract the module-level docstring from a Python file using AST."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
        return ast.get_docstring(tree)
    except Exception:
        return None


def _extract_md_frontmatter(path: str) -> str | None:
    """Extract YAML frontmatter (between --- delimiters) from a Markdown file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            first_line = f.readline().rstrip("\n")
            if first_line != "---":
                return None
            lines = []
            for line in f:
                if line.rstrip("\n") == "---":
                    break
                lines.append(line.rstrip("\n"))
            else:
                return None  # no closing ---
            return "\n".join(lines) if lines else None
    except Exception:
        return None


def _extract_leading_comment(path: str, ext: str) -> str | None:
    """Extract the leading comment block from a source file.

    Handles line comments (// # -- etc.) and block comments (/* */ <!-- --> etc.).
    Skips shebangs (#!) at the top.
    """
    style = _COMMENT_STYLES.get(ext)
    if style is None:
        return None

    line_pfx, block_open, block_close = style

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_lines = []
            for line in f:
                raw_lines.append(line.rstrip("\n"))
                if len(raw_lines) >= 50:  # cap how far we look
                    break
    except Exception:
        return None

    if not raw_lines:
        return None

    idx = 0

    # skip blank lines at the top, then skip shebang if present
    while idx < len(raw_lines) and not raw_lines[idx].strip():
        idx += 1

    if idx < len(raw_lines) and raw_lines[idx].startswith("#!"):
        idx += 1

    # skip blank lines after shebang
    while idx < len(raw_lines) and not raw_lines[idx].strip():
        idx += 1

    if idx >= len(raw_lines):
        return None

    collected: list[str] = []

    # try block comment first
    if block_open and block_close and raw_lines[idx].lstrip().startswith(block_open):
        first = raw_lines[idx]
        # strip the block open marker (and extra * for javadoc style /**)
        content = first.lstrip()
        content = content[len(block_open):]
        content = content.lstrip("*")

        # single-line block comment?  e.g. /* foo */
        if block_close in content:
            content = content[:content.index(block_close)]
            stripped = content.strip()
            return stripped if stripped else None

        if content.strip():
            collected.append(content.strip())

        idx += 1
        while idx < len(raw_lines):
            line = raw_lines[idx]
            if block_close in line:
                before_close = line[:line.index(block_close)]
                # strip leading * for javadoc style
                cleaned = before_close.strip().lstrip("*").strip()
                if cleaned:
                    collected.append(cleaned)
                break
            # strip leading * or leading whitespace
            cleaned = line.strip().lstrip("*").strip()
            collected.append(cleaned)
            idx += 1

        return "\n".join(collected).strip() or None

    # try line comments
    if line_pfx and raw_lines[idx].lstrip().startswith(line_pfx):
        while idx < len(raw_lines):
            stripped = raw_lines[idx].lstrip()
            if not stripped.startswith(line_pfx):
                break
            # remove the prefix and one optional space
            text = stripped[len(line_pfx):]
            if text.startswith(" "):
                text = text[1:]
            collected.append(text)
            idx += 1

        return "\n".join(collected).strip() or None

    return None


def _extract_identity(path: str) -> tuple[str, str | None]:
    """Extract the identity string for any file. Returns (method, content)."""
    ext = Path(path).suffix.lower()
    name = Path(path).name.lower()

    # special case: Dockerfile has no extension
    if name == "dockerfile" or name.startswith("dockerfile."):
        ext = ".dockerfile"

    # Python: AST docstring is best
    if ext == ".py":
        doc = _extract_py_docstring(path)
        if doc:
            return ("docstring", doc)
        # fall through to leading comment
        comment = _extract_leading_comment(path, ext)
        return ("comment", comment) if comment else ("none", None)

    # Markdown: YAML frontmatter
    if ext == ".md":
        fm = _extract_md_frontmatter(path)
        if fm:
            return ("frontmatter", fm)
        return ("none", None)

    # Everything else: leading comment block
    comment = _extract_leading_comment(path, ext)
    if comment:
        return ("comment", comment)

    return ("none", None)


# ── file walker (all types, not just .py/.md) ───────────────────────

def _iter_all_files(
    roots: list[Union[str, Path]],
    excl_dirs: set[str],
    excl_files: set[str],
    excl_types: set[str],
    patterns,
) -> list[str]:
    """Walk roots and return sorted list of all non-binary, non-excluded files."""
    paths = [Path(r) if not isinstance(r, Path) else r for r in roots]
    stack = list(paths)
    results = []

    while stack:
        cur = stack.pop()

        if cur.is_file():
            results.append(str(cur))
            continue

        try:
            with os.scandir(cur) as it:
                entries = sorted(it, key=lambda e: e.name.lower())
        except (PermissionError, NotADirectoryError, FileNotFoundError):
            continue

        for e in entries:
            if e.is_dir(follow_symlinks=False):
                if e.name.lower() not in excl_dirs and not any(
                    rx.fullmatch(e.name) for rx in patterns
                ):
                    stack.append(Path(e.path))
            else:
                lo = e.name.lower()
                if any(lo.endswith(ext) for ext in BINARY_EXTENSIONS):
                    continue
                if lo in excl_files:
                    continue
                if any(lo.endswith(ext) for ext in excl_types):
                    continue
                if any(rx.fullmatch(e.name) for rx in patterns):
                    continue
                results.append(str(e.path))

    results.sort(key=lambda p: p.lower())
    return results


# ── main entry point ────────────────────────────────────────────────

def generate_manifest(
    directory: str,
    output_filepath: str,
    *,
    exclude_tests: bool = False,
    user_excludes: Iterable[str] | None = None,
    only: str | None = None,
    status_cb: Callable[[str, Any], None] | None = None,
) -> None:
    """Generate a manifest .md with extracted identity for every file."""
    # Build exclusions (same logic as documentation.py)
    dirs = list(DEFAULT_EXCLUDED_DIRECTORIES)
    files = list(DEFAULT_EXCLUDED_FILES)
    patterns = list(DEFAULT_EXCLUDED_FILE_PATTERNS)
    types = set(DEFAULT_EXCLUDED_FILE_TYPES)

    if exclude_tests:
        patterns.append("*_test.*")
    if user_excludes:
        dirs += [os.path.basename(p.strip("/\\")) for p in user_excludes]
        files += [os.path.basename(p.strip("/\\")) for p in user_excludes]

    excluded_dirs, excluded_files, compiled_patterns = normalize_exclusions(dirs, files, patterns)

    roots: list[Path] = []
    if only:
        for p in (s.strip() for s in only.split(",")):
            ab = Path(p).expanduser()
            try:
                roots.append(ab.resolve(strict=True))
            except FileNotFoundError:
                logging.warning("[recon] Skipping missing path: %s", ab)
    if not roots:
        roots = [Path(directory)]

    all_files = _iter_all_files(
        list(roots), excluded_dirs, excluded_files, types, compiled_patterns
    )
    total = len(all_files)
    if status_cb:
        status_cb("walk", total)

    # Collect entries grouped by extraction method
    entries: list[tuple[str, str, str | None]] = []  # (rel, method, content)

    for idx, path in enumerate(all_files, 1):
        if status_cb:
            status_cb("read", (idx, total))
        rel = os.path.relpath(path, directory).replace(os.sep, "/")
        method, content = _extract_identity(path)
        entries.append((rel, method, content))

    if status_cb:
        status_cb("write", None)

    with open(output_filepath, "w", encoding="utf-8") as md:
        md.write(f"# Project Manifest — {os.path.basename(directory)}\n\n")

        md.write("## Directory Tree\n\n")
        md.write(generate_directory_tree(
            directory=directory,
            excluded_dirs=list(excluded_dirs),
            excluded_files=list(excluded_files),
            excluded_patterns=patterns,
        ) + "\n\n")

        # Files with identity
        has_identity = [(r, m, c) for r, m, c in entries if c]
        no_identity = [r for r, m, c in entries if not c]

        if has_identity:
            md.write("## File Identities\n\n")
            for rel, method, content in has_identity:
                md.write(f"### `{rel}`\n")
                lang = "yaml" if method == "frontmatter" else ""
                md.write(f"```{lang}\n{content}\n```\n\n")

        if no_identity:
            md.write("## Files Without Identity\n\n")
            for rel in no_identity:
                md.write(f"- `{rel}`\n")
            md.write("\n")

    logging.info("Manifest saved → %s", output_filepath)
