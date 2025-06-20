"""
Traceframe – directory_tree.py
Iterative, allocation‑light directory tree writer.
"""

from __future__ import annotations
import os, fnmatch
from typing import List
from .config import (
    DEFAULT_EXCLUDED_DIRECTORIES,
    DEFAULT_EXCLUDED_FILES,
    DEFAULT_EXCLUDED_FILE_PATTERNS,
)

def generate_directory_tree(
    directory: str = ".",
    excluded_dirs: List[str] = None,
    excluded_files: List[str] = None,
    excluded_patterns: List[str] = None,
) -> str:
    """
    Generate a directory tree as a string, excluding specified directories and files.
    """
    excluded_dirs = excluded_dirs or list(DEFAULT_EXCLUDED_DIRECTORIES)
    excluded_files = excluded_files or list(DEFAULT_EXCLUDED_FILES)
    excluded_patterns = excluded_patterns or list(DEFAULT_EXCLUDED_FILE_PATTERNS)

    tree = []
    for root, dirs, files in os.walk(directory):
        # Exclude directories
        dirs[:] = [d for d in dirs if d not in excluded_dirs]

        # Exclude files
        files = [
            f for f in files
            if f not in excluded_files and not any(fnmatch.fnmatch(f, pattern) for pattern in excluded_patterns)
        ]

        # Add the current directory to the tree
        level = root.replace(directory, "").count(os.sep)
        indent = "    " * level
        tree.append(f"{indent}├── {os.path.basename(root)}/")

        # Add the files in the current directory
        sub_indent = "    " * (level + 1)
        for file in files:
            tree.append(f"{sub_indent}├── {file}")

    return "\n".join(tree)
