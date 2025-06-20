# config.py

# Sensitive keys that should be masked when encountered in JSON data
SENSITIVE_KEYS = {"secret_env","key_env","api_key","token","secret","password","credentials","auth_token"}

# Output file names
DIRECTORY_TREE_FILENAME = "directory_tree.txt"
DOCUMENTATION_FILENAME = "project_structure_{timestamp}.md"

# Default exclusions for documentation
DEFAULT_EXCLUDED_DIRECTORIES = {"tmp", ".venv", "__pycache__", "node_modules", ".git", "LICENSE", "migrations", "air", "dummy", ".bin", ".pytest_cache"}
DEFAULT_EXCLUDED_FILES = {DIRECTORY_TREE_FILENAME,"__init__.py","README.md", "project_structure.md", ".gitignore", "LICENSE", "application.log", "site.db", "go.sum", "todo.md"}
DEFAULT_EXCLUDED_FILE_PATTERNS = ["application_*.log", "project_structure_*.md", "*_test.*", "conversation.txt", "*.pyc", "*.cache", "*.log"]
DEFAULT_EXCLUDED_FILE_TYPES = {".png", ".jpg", ".jpeg", ".gif", ".pyc", ".bin", ".exe", ".dll"}

# New additions for file exclusions
DEFAULT_EXCLUDED_FILES.update({"trading_bot_data.sqlite", "orders.db", "tigerbeetle.zip"})
DEFAULT_EXCLUDED_FILE_TYPES.update({".sqlite", ".db", ".zip"})

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

# Exclusions for the directory tree generation
DIRECTORY_TREE_EXCLUDE_FILES = {"go.mod", "go.sum", "*.log", "application_*.log", "project_structure_*.md"}
DIRECTORY_TREE_EXCLUDE_DIRS = {"tmp", ".vscode", ".bin", ".venv", "venv", "__pycache__", "Conversations", "conversations Test", ".git", "dummy"}
DIRECTORY_TREE_EXCLUDE_EXTS = {".log", ".md"}

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
