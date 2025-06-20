"""
Traceframe – file_operations.py
Delete stale artefacts but never today’s live log file.
"""
import logging, os, glob
from datetime import datetime
from .config import DELETE_OLD_FILE_PATTERNS

_TODAY_LOG = f"application_{datetime.now():%Y-%m-%d}.log"

def delete_old_files(directory: str) -> None:
    for pattern, description in DELETE_OLD_FILE_PATTERNS.items():
        for path in glob.glob(os.path.join(directory, pattern)):
            # never remove today’s live log
            if os.path.basename(path) == _TODAY_LOG:
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
    out = []
    for line in content.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            if len(v) > 10:
                v = v[:10] + "***"
            out.append(f"{k}={v}")
        else:
            out.append(line)
    return "\n".join(out)
