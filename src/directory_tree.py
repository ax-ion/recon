"""
Recon – directory_tree.py
Iterative, allocation‑light directory tree writer.
"""

from __future__ import annotations

import os
import re
from typing import List, Optional

from .config import (DEFAULT_EXCLUDED_DIRECTORIES,
                     DEFAULT_EXCLUDED_FILE_PATTERNS, DEFAULT_EXCLUDED_FILES,
                     normalize_exclusions)


def generate_directory_tree(
    directory: str = ".",
    excluded_dirs: Optional[List[str]] = None,
    excluded_files: Optional[List[str]] = None,
    excluded_patterns: Optional[List[str]] = None,
) -> str:
    """
    Generate a directory tree as a string, excluding specified directories and files.
    """
    # Normalize and validate exclusions
    norm_dirs, norm_files, compiled_patterns = normalize_exclusions(
        list(excluded_dirs) if excluded_dirs is not None else list(DEFAULT_EXCLUDED_DIRECTORIES),
        list(excluded_files) if excluded_files is not None else list(DEFAULT_EXCLUDED_FILES),
        list(excluded_patterns) if excluded_patterns is not None else list(DEFAULT_EXCLUDED_FILE_PATTERNS),
    )

    tree: List[str] = []
    for root, dirs, files in os.walk(directory):
        # Exclude directories
        dirs[:] = [
            d for d in dirs
            if d.lower() not in norm_dirs and not any(rx.fullmatch(d) for rx in compiled_patterns)
        ]

        # Exclude files
        files = [
            f for f in files
            if f.lower() not in norm_files and not any(rx.fullmatch(f) for rx in compiled_patterns)
        ]
        # Add the current directory to the tree
        level = root.replace(directory, "").count(os.sep)
        indent = "    " * level
        tree.append(f"{indent}├── {os.path.basename(root)}/")

        # Add filtered files
        sub_indent = "    " * (level + 1)
        for file in files:
            tree.append(f"{sub_indent}├── {file}")

    return "\n".join(tree)
