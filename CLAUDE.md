# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Recon is a CLI tool that generates Markdown documentation and ASCII directory trees from project source code. It streams files with constant memory, masks sensitive data (.env values, JSON keys like `api_key`, `password`, `token`), and copies output to clipboard via pyperclip.

## Running

```bash
# Standard run (from target project directory)
python main.py

# Common flags
python main.py -s src,utils          # document only matching path suffixes
python main.py -f path/to/file.py    # document a single file
python main.py --fast                # tree-only mode, skip file contents
python main.py --auto-deps app.py    # resolve Python imports and document dependencies
python main.py -x migrations,venv   # exclude by base name
python main.py -G                    # include *_test files (excluded by default)
python main.py -o out.md             # custom output file path
python main.py --no-clipboard        # skip copying output to clipboard
python main.py --debug               # verbose logging + log file creation
python main.py --profile             # write recon_profile.csv with timing

# Dev launcher (runs from a specific git branch, then returns to master)
python dev_run.py -b feature-branch [main.py flags]

# Shell launchers (wrappers around main.py)
./launch           # bash
./launch.bat       # Windows CMD
./run_recon.sh     # bash (minimal)
```

The tool runs in the **current working directory** (not its own directory). Output is `project_structure_{timestamp}.md` in cwd.

## Architecture

Entry point is `main.py` which orchestrates: CLI parsing -> cleanup -> threaded progress ticker -> documentation generation -> clipboard copy -> post-run cleanup.

All core logic lives in `src/`:

- **config.py** - All exclusion sets (directories, files, patterns, extensions), `BINARY_EXTENSIONS` frozenset, sensitive key list, language map for syntax highlighting, and `normalize_exclusions()` which compiles fnmatch patterns to regex
- **documentation.py** - Streaming generator (`generate_documentation`). Processes files one at a time. Handles JSON masking, CSV/TSV truncation, repetition summarization. This is where the bulk of the logic lives
- **file_operations.py** - File deletion, path normalization, `.env` masking, `fuzzy_find()` for `-s` flag resolution, `resolve_import_dependencies()` using Python AST
- **directory_tree.py** - Iterative tree writer using `os.walk()` with exclusion filtering
- **logging_config.py** - UTF-8 logging setup with Windows console encoding fix (ctypes)

## Key Design Decisions

- **Streaming generator**: `documentation.py` yields file content one at a time rather than building a list in memory. This is intentional for large codebases.
- **Runs in cwd**: The tool documents whatever directory you run it from, not its own source directory. `os.getcwd()` is the target.
- **Post-run cleanup**: After generating docs, `main.py` walks BASE_DIR (recon's own directory) to delete `__pycache__`, `.pytest_cache`, old logs, and old `project_structure_*.md` files. The `-N` flag skips pre-run cleanup only.
- **Fuzzy path resolution**: The `-s` flag first tries exact path match, then falls back to suffix-based fuzzy search via `os.walk` with directory pruning. Ambiguous matches cause an interactive prompt and exit.
- **Clipboard is opt-out**: Use `--no-clipboard` to skip. Failure is caught and logged.

## Dependencies

Only external dependency is `pyperclip`. Everything else is stdlib. Install via `pip install -r requirements.txt`.
