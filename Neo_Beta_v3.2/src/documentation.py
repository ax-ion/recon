"""
Traceframe – documentation.py  · 2025‑05‑08
Streaming generator with live progress callbacks.

Why this version?
─────────────────
• Absolutely no “giant list of file‑bodies” → constant memory, even on TB trees
• Compiled regex + os.scandir for fast exclusion
• status_cb(label, data) fired for ‘walk’, ‘read’, ‘write’ so main.py’s
  ticker shows real‑time progress
"""

from __future__ import annotations
import os, fnmatch, json, logging, re
from pathlib import Path
from typing  import Callable, Iterable, Iterator, Any

# ─── local imports ────────────────────────────────────────────────────────────
from .directory_tree import generate_directory_tree
from .file_operations import mask_sensitive_data
from .config import (
    DEFAULT_EXCLUDED_DIRECTORIES as _DEF_DIRS,
    DEFAULT_EXCLUDED_FILES       as _DEF_FILES,
    DEFAULT_EXCLUDED_FILE_PATTERNS,
    DEFAULT_EXCLUDED_FILE_TYPES  as _DEF_TYPES,
    LANGUAGE_MAP,
    SENSITIVE_KEYS,
)

# ─── constants / compiled patterns ────────────────────────────────────────────
_BIN = tuple(e.lower() for e in (
    ".jpg",".jpeg",".png",".gif",".bmp",".tiff",".webp",
    ".mov",".mp4",".mkv",".avi",
    ".wav",".mp3",".flac",
    ".pdf",".zip",".rar",".gz",".7z",
    ".exe",".dll",
))
_PAT = [re.compile(fnmatch.translate(p)) for p in DEFAULT_EXCLUDED_FILE_PATTERNS]

def _skip(name:str,
          excl_files:set[str],
          excl_types:set[str]) -> bool:
    lo = name.lower()
    if lo.endswith(_BIN):                         return True
    if lo in excl_files:                          return True
    if any(lo.endswith(ext) for ext in excl_types): return True
    return any(rx.fullmatch(name) for rx in _PAT)

# ─── masking helpers ──────────────────────────────────────────────────────────
def _mask_json(txt:str) -> str|None:
    try:
        obj = json.loads(txt)
    except json.JSONDecodeError:
        return None
    def _scrub(v):
        if isinstance(v,dict):
            return {k: ("*"*len(x) if k in SENSITIVE_KEYS and isinstance(x,str) else _scrub(x))
                    for k,x in v.items()}
        if isinstance(v,list):
            return [_scrub(x) for x in v]
        return v
    return json.dumps(_scrub(obj), indent=2)

def _dump_one(md, base:str, abs_path:str, text:str) -> None:
    rel  = os.path.relpath(abs_path, base).replace(os.sep,"/")
    lang = LANGUAGE_MAP.get(Path(abs_path).suffix, "text")

    if rel.endswith(".env"):
        text = mask_sensitive_data(text)
    elif rel.endswith(".json"):
        masked = _mask_json(text)
        if masked is None: return
        text = masked

    fence = "````" if rel.lower().endswith(".md") else "```"
    md.write(f"- `{rel}`:\n")
    md.write(f"    {fence}{lang}\n")
    for line in text.splitlines():
        md.write(f"    {line}\n")
    md.write(f"    {fence}\n")

# ─── low‑memory walker ────────────────────────────────────────────────────────
def _iter_files(roots:list[str],
                excl_dirs:set[str],
                excl_files:set[str],
                excl_types:set[str]) -> Iterator[str]:
    stack = [Path(r) for r in roots]
    while stack:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                entries = sorted(it, key=lambda e: e.name.lower())
        except PermissionError:
            continue

        # separate dirs & files to get predictable ordering
        dirs  = [e for e in entries if e.is_dir(follow_symlinks=False)]
        files = [e for e in entries if not e.is_dir(follow_symlinks=False)]

        for d in reversed(dirs):                     # depth‑first
            if d.name in excl_dirs:  continue
            if _skip(d.name, set(), set()): continue
            stack.append(d.path)

        for f in files:
            if _skip(f.name, excl_files, excl_types): continue
            yield f.path

# ─── public API ───────────────────────────────────────────────────────────────
def generate_documentation(
        directory      : str,
        output_filepath: str,
        *,
        exclude_tests : bool  = False,
        user_excludes : Iterable[str] | None = None,
        only          : str | None = None,
        specific_file : str | None = None,  # New parameter for a specific file
        fast_tree_only: bool = False,
        status_cb     : Callable[[str, Any], None] | None = None
    ) -> None:
    """
    Stream Markdown documentation for *directory* or a specific file to *output_filepath*.

    status_cb(label, data) receives:
        • ("walk",  total_files)
        • ("read", (idx, total))
        • ("write", None)
    """
    # ── handle specific file ────────────────────────────────────────────────
    if specific_file:
        specific_file_path = Path(specific_file).resolve()
        if not specific_file_path.exists():
            logging.error("Specified file does not exist: %s", specific_file)
            return

        with open(output_filepath, "w", encoding="utf‑8") as md:
            md.write(f"## Documentation for {specific_file}\n\n")
            try:
                with open(specific_file_path, "r", encoding="utf‑8") as f:
                    text = f.read()
                _dump_one(md, specific_file_path.parent, str(specific_file_path), text)
            except Exception as e:
                logging.error("Failed to process file %s: %s", specific_file, e)
        logging.info("Documentation saved → %s", output_filepath)
        return

    # ── build exclusion sets ────────────────────────────────────────────────
    excluded_dirs = set(_DEF_DIRS)
    excluded_files = set(_DEF_FILES)
    excluded_patterns = [str(pattern) for pattern in DEFAULT_EXCLUDED_FILE_PATTERNS]  # Ensure patterns are strings

    if exclude_tests:
        excluded_patterns.append(fnmatch.translate("*_test.*"))
    if user_excludes:
        excluded_dirs.update(user_excludes)

    # ── resolve roots / --specific -----------------------------------------
    roots:list[str] = []
    if only:
        for p in (s.strip() for s in only.split(",")):
            ab = (Path(directory)/p).expanduser()
            if ab.exists():
                roots.append(str(ab.resolve()))
    if not roots:
        roots = [directory]

    # ── write header + directory tree --------------------------------------
    with open(output_filepath, "w", encoding="utf‑8") as md:
        md.write(f"## Project Directory Structure of {directory}\n\n")
        md.write(generate_directory_tree(
            directory=directory,
            excluded_dirs=list(excluded_dirs),
            excluded_files=list(excluded_files),
            excluded_patterns=excluded_patterns,
        ) + "\n\n")

        if fast_tree_only:
            logging.info("Fast tree‑only mode completed.")
            return

        # ── WALK phase – count & yield paths --------------------------------
        for root, dirs, files in os.walk(directory):
            # Exclude directories
            dirs[:] = [d for d in dirs if d not in excluded_dirs]

            # Exclude files
            files = [
                f for f in files
                if f not in excluded_files and not any(fnmatch.fnmatch(f, pattern) for pattern in excluded_patterns)
            ]

            # Process remaining files and directories
            for file in files:
                abs_path = os.path.join(root, file)
                try:
                    with open(abs_path, "r", encoding="utf‑8") as f:
                        text = f.read()
                except Exception:
                    continue
                _dump_one(md, directory, abs_path, text)
                if status_cb and files.index(file) % 25 == 0:
                    status_cb("read", (files.index(file) + 1, len(files)))

            if status_cb:
                status_cb("walk", len(files))

        if status_cb:
            status_cb("write", None)

    logging.info("Documentation saved → %s", output_filepath)
