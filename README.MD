# Recon

Reconnaissance on your codebase. Fast docs, directory trees, and project maps built for AI.

## What It Does

Recon scans your project directory and generates:

- Clean Markdown documentation from all readable source files
- A visual, structured directory tree of your codebase
- Masked sensitive data (`.env` values, API keys, passwords)
- Smart exclusion rules for noise-free output
- Clipboard-ready output for pasting into AI conversations

## Usage

```bash
recon                              # full docs + tree
recon --fast                       # tree only
recon -s src,utils                 # specific paths only
recon -f path/to/file.py           # single file
recon --auto-deps app.py           # follow Python imports
recon -o out.md --no-clipboard     # custom output, skip clipboard
recon -x migrations,venv           # exclude by name
recon --debug                      # verbose logging
```

## Why Recon?

- Distill your codebase into something an AI can actually use
- No bloat — only the files that matter
- Secrets stay secret

---

Built for speed. Tuned for clarity.
