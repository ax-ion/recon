# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Recon is a CLI tool that generates Markdown documentation and ASCII directory trees from project source code. It's designed for AI agents and humans to quickly understand any codebase. It streams files with constant memory, masks sensitive data, redacts PII, and copies output to clipboard.

## Running

```bash
# Standard run (from target project directory)
python main.py

# Common flags
python main.py -s src,utils          # document only matching path suffixes
python main.py -f path/to/file.py    # document a single file
python main.py --fast                # tree-only mode, skip file contents
python main.py --manifest            # identity-only mode (frontmatter + docstrings)
python main.py --auto-deps app.py    # resolve Python imports and document dependencies
python main.py -x migrations,venv   # exclude by base name
python main.py -G                    # include *_test files (excluded by default)
python main.py -o out.md             # custom output file path
python main.py --no-clipboard        # skip copying output to clipboard
python main.py --debug               # verbose logging + log file creation
python main.py --profile             # write recon_profile.csv with timing

# Redaction (standalone)
python -m src.redact input.pdf --profiles ssn ein bank --dry-run
python -m src.redact input.pdf --all --names "John Doe,Jane Doe"

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
- **documentation.py** - Streaming generator (`generate_documentation`). Processes files one at a time. Handles JSON masking, CSV/TSV truncation, repetition summarization
- **manifest.py** - Extracts file identity (docstrings, frontmatter, leading comments) for 50+ file types. Produces condensed overview without full file contents
- **redact.py** - Configurable PII redaction for PDFs and text files. 9 profiles: ssn, ein, bank, routing, credit, phone, email, address, apikey. Plus custom name matching
- **file_operations.py** - File deletion, path normalization, `.env` masking, `fuzzy_find()` for `-s` flag resolution, `resolve_import_dependencies()` using Python AST
- **directory_tree.py** - Iterative tree writer using `os.walk()` with exclusion filtering
- **logging_config.py** - UTF-8 logging setup with Windows console encoding fix (ctypes)

## Layered Configuration Architecture

Recon follows the **layered/cascading configuration** pattern used by Git, npm, ESLint, Claude Code, and most serious CLI tools. Config resolution order (last wins):

```
Defaults (config.py)           ← hardcoded sensible defaults
  └─ User config (~/.config/recon/config.yaml)  ← personal preferences
      └─ Project config (.recon/config.yaml)     ← project-specific overrides
          └─ CLI flags (--exclude, --fast, etc.)  ← invocation-time overrides
```

### Project config: `.recon/`

Every project that uses Recon can have a `.recon/` directory:

```
.recon/
├── config.yaml        # project-specific exclusions, output prefs, redaction profiles
└── identities.yaml    # manual descriptions for files that can't self-describe
```

**`identities.yaml`** solves the "files without identity" problem. Files like `.json`, `.env`, configs, and extensionless scripts can't hold comments or frontmatter. The sidecar file provides their descriptions, which `--manifest` merges with auto-extracted identity.

### User config: `~/.config/recon/`

Global defaults that apply to every project unless overridden:

```
~/.config/recon/
└── config.yaml        # default exclusions, preferred output format, etc.
```

### When contributing to Recon

Any new feature should respect this cascade. If you're adding a config option:
1. Add a default in `config.py`
2. Make it overridable from `.recon/config.yaml`
3. Make it overridable from CLI flags
4. Document the flag in `_cli()` in `main.py`

## Key Design Decisions

- **Streaming generator**: `documentation.py` yields file content one at a time rather than building a list in memory. This is intentional for large codebases.
- **Runs in cwd**: The tool documents whatever directory you run it from, not its own source directory. `os.getcwd()` is the target.
- **Post-run cleanup**: After generating docs, `main.py` walks BASE_DIR (recon's own directory) to delete `__pycache__`, `.pytest_cache`, old logs, and old `project_structure_*.md` files. The `-N` flag skips pre-run cleanup only.
- **Fuzzy path resolution**: The `-s` flag first tries exact path match, then falls back to suffix-based fuzzy search via `os.walk` with directory pruning. Ambiguous matches cause an interactive prompt and exit.
- **Clipboard is opt-out**: Use `--no-clipboard` to skip. Failure is caught and logged.
- **Manifest as progressive disclosure**: `--manifest` extracts only the identity layer (frontmatter, docstrings, leading comments). This is the lightweight map an AI loads first — full file contents only when needed.
- **Layered config**: Project overrides user overrides defaults. CLI flags override everything. This pattern must be maintained as features are added.

## Dependencies

Core: `pyperclip` (clipboard). Optional: `PyMuPDF` (PDF redaction). Everything else is stdlib. Install via `pip install -r requirements.txt`.
