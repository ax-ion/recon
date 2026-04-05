# config.py

# Sensitive keys that should be masked when encountered in JSON data
SENSITIVE_KEYS = {"secret_env","key_env","api_key","token","secret","password","credentials","auth_token"}

# Output file names
DIRECTORY_TREE_FILENAME = "directory_tree.txt"
DOCUMENTATION_FILENAME = "project_structure_{timestamp}.md"

# Default exclusions for documentation
DEFAULT_EXCLUDED_DIRECTORIES = {"tmp", ".venv", "__pycache__", "node_modules", ".git", "LICENSE", "migrations", "air", "dummy", ".bin", ".pytest_cache"}
DEFAULT_EXCLUDED_FILES = {DIRECTORY_TREE_FILENAME,"README.md", "project_structure.md", ".gitignore", "LICENSE", "application.log", "site.db", "go.sum", "todo.md"}
DEFAULT_EXCLUDED_FILE_PATTERNS = ["application_*.log", "project_structure_*.md", "*_test.*", "conversation.txt", "*.pyc", "*.cache", "*.log"]
DEFAULT_EXCLUDED_FILE_TYPES = {".png", ".jpg", ".jpeg", ".gif", ".pyc", ".bin", ".exe", ".dll"}

# New additions for file exclusions
DEFAULT_EXCLUDED_FILES.update({"trading_bot_data.sqlite", "orders.db", "tigerbeetle.zip"})
DEFAULT_EXCLUDED_FILE_TYPES.update({".sqlite", ".db", ".zip"})

# Binary extensions — skip entirely (no attempt to read)
BINARY_EXTENSIONS = frozenset((
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp",
    ".mov", ".mp4", ".mkv", ".avi",
    ".wav", ".mp3", ".flac",
    ".pdf", ".zip", ".rar", ".gz", ".7z",
    ".exe", ".dll",
))

# Dynamic updates for exclusions or inclusions
RUNTIME_EXCLUSIONS = {
    "files": set(),
    "dirs": set(),
    "patterns": set(),
}

# Language map for syntax highlighting in documentation
LANGUAGE_MAP = {
    '.py': 'python', '.js': 'javascript', '.html': 'html',
    '.css': 'css', '.md': 'markdown', '.txt': 'plaintext', '.lua': 'lua', '.go': 'go', '.json': 'json'
}

# Old file patterns for deletion
DELETE_OLD_FILE_PATTERNS = {
    'project_structure_*.md': "Old documentation files",
    'application_*.log': "Log files"
}

# Files and directories to delete during cleanup
FILES_TO_DELETE = {
    "application_*.log",
    "directory_tree.txt",
    "project_structure_*.md",
}
DIRECTORIES_TO_DELETE = {
    "__pycache__",
    ".pytest_cache",
}

CSV_TRUNCATE_LIMIT = 100
REPETITION_THRESHOLD = 3
JSON_REPETITION_TRIM_THRESHOLD = 5

import fnmatch
import os
import re
from typing import List, Tuple


def normalize_exclusions(
    dirs: List[str],
    files: List[str],
    patterns: List[str]
) -> Tuple[set[str], set[str], List[re.Pattern]]:
    """
    Normalize and compile exclusion lists.

    - Converts dir/file names to lowercase
    - Extracts basename from paths
    - Compiles fnmatch-style patterns to regex

    Returns:
        (excluded_dirs, excluded_files, compiled_patterns)
    """
    excluded_dirs = set(os.path.basename(d.strip("/\\").lower()) for d in dirs)
    excluded_files = set(os.path.basename(f.strip("/\\").lower()) for f in files)
    compiled_patterns = [re.compile(fnmatch.translate(p)) for p in patterns]
    return excluded_dirs, excluded_files, compiled_patterns
