
# Traceframe

A fast and customizable documentation + directory tree generator for Python projects.

## 🔍 What It Does

Traceframe scans your project directory and generates:

- 📄 Clean Markdown documentation from all readable source files
- 🌲 A visual, structured directory tree of your codebase
- 🧼 Masked sensitive data (e.g., `.env`, `api_key`, `password`)
- 🔍 Explicit targeting of specific files/folders
- 🔁 Smart exclusion rules for noise-free output
- 📝 A UTF‑8 log file with every run

## 🚀 Usage

Run with:

```bash
traceframe -s src,utils --no-clipboard
```

Options include:

- `--specific`: Process only listed paths
- `--exclude`: Skip noisy folders like `.git`, `__pycache__`, etc.
- `--no-delete`: Keep old logs/docs
- `--debug`: See internal operations in terminal

## 💡 Why Use Traceframe?

- Stop bloated doc generation
- Focus only on what matters
- Rapidly visualize, document, and share your codebase

---

Built for speed. Tuned for clarity.
