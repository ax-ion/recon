"""
Recon – documentation.py · 2025‑05‑08
Streaming generator with live progress callbacks.

Why this version?
─────────────────
• Absolutely no “giant list of file‑bodies” → constant memory, even on TB trees
• Centralized exclusion logic via config.normalize_exclusions()
• status_cb(label, data) fired for ‘walk’, ‘read’, ‘write’ so main.py’s ticker shows real‑time progress
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Union
from .config import (DEFAULT_EXCLUDED_DIRECTORIES,
                     DEFAULT_EXCLUDED_FILE_PATTERNS,
                     DEFAULT_EXCLUDED_FILE_TYPES, DEFAULT_EXCLUDED_FILES,
                     LANGUAGE_MAP, SENSITIVE_KEYS, BINARY_EXTENSIONS,
                     normalize_exclusions,
                     CSV_TRUNCATE_LIMIT, REPETITION_THRESHOLD, JSON_REPETITION_TRIM_THRESHOLD)
from .directory_tree import generate_directory_tree
from .file_operations import mask_sensitive_data


def _skip(name: str, excl_files: set[str], excl_types: set[str], patterns) -> bool:
    lo = name.lower()
    if any(lo.endswith(ext) for ext in BINARY_EXTENSIONS):
        return True
    if lo in excl_files:
        return True
    if any(lo.endswith(ext) for ext in excl_types):
        return True
    return any(rx.fullmatch(name) for rx in patterns)


def _mask_json(txt: str) -> str | None:
    try:
        obj = json.loads(txt)
    except json.JSONDecodeError:
        return None

    def is_repeating_dict_list(lst):
        if not lst or not isinstance(lst, list) or not all(isinstance(x, dict) for x in lst):
            return False
        first_keys = set(lst[0].keys())
        return all(set(x.keys()) == first_keys for x in lst[1:])

    def _scrub(v):
        if isinstance(v, dict):
            return {
                k: ("*" * len(x) if k in SENSITIVE_KEYS and isinstance(x, str) else _scrub(x))
                for k, x in v.items()
            }
        if isinstance(v, list):
            if len(v) > JSON_REPETITION_TRIM_THRESHOLD and is_repeating_dict_list(v):
                return [_scrub(x) for x in v[:JSON_REPETITION_TRIM_THRESHOLD]] + [
                    {"__recon_note__": f"... {len(v) - JSON_REPETITION_TRIM_THRESHOLD} items removed for brevity"}
                ]
            return [_scrub(x) for x in v]
        return v

    return json.dumps(_scrub(obj), indent=2)


def summarize_repetitions(lines: list[str], threshold: int) -> list[str]:
    output = []
    i = 0
    while i < len(lines):
        line = lines[i]
        count = 1
        while i + count < len(lines) and lines[i + count] == line:
            count += 1
        if count > threshold:
            output.append(f"{line}  # [repeated x{count}, removed for brevity]")
            i += count
        else:
            output.extend(lines[i:i+count])
            i += count
    return output

def _dump_one(md, base: str, abs_path: str, text: str) -> None:
    rel = os.path.relpath(abs_path, base).replace(os.sep, "/")
    lang = LANGUAGE_MAP.get(Path(abs_path).suffix, "text")

    if rel.endswith(".env"):
        text = mask_sensitive_data(text)
    elif rel.endswith(".json"):
        masked = _mask_json(text)
        if masked is None:
            return
        text = masked

    elif rel.endswith(".csv") or rel.endswith(".tsv"):
        rows = text.splitlines()
        if len(rows) > CSV_TRUNCATE_LIMIT:
            head = rows[:5]
            tail = rows[-3:]
            summary = [f"# [middle rows truncated for brevity, total rows={len(rows)}]"]
            text = "\n".join(head + summary + tail)

    fence = "````" if rel.lower().endswith(".md") else "```"
    md.write(f"- `{rel}`:\n")
    md.write(f"    {fence}{lang}\n")
    clean_lines = summarize_repetitions(text.splitlines(), REPETITION_THRESHOLD)
    for line in clean_lines:
        md.write(f"    {line}\n")
    md.write(f"    {fence}\n")

def _iter_files(
    roots: list[Union[str, Path]],
    excl_dirs: set[str],
    excl_files: set[str],
    excl_types: set[str],
    patterns
) -> Iterator[str]:
    paths: list[Path] = [Path(r) if not isinstance(r, Path) else r for r in roots]
    stack = list(paths)

    while stack:
        cur = stack.pop()

        if cur.is_file():
            yield str(cur)
            continue

        try:
            with os.scandir(cur) as it:
                entries = sorted(it, key=lambda e: e.name.lower())
        except (PermissionError, NotADirectoryError, FileNotFoundError):
            continue

        dirs = [e for e in entries if e.is_dir(follow_symlinks=False)]
        files = [e for e in entries if not e.is_dir(follow_symlinks=False)]

        for d in reversed(dirs):
            if _skip(d.name, excl_files=set(), excl_types=set(), patterns=patterns) or d.name.lower() in excl_dirs:
                continue
            stack.append(Path(d.path))

        for f in files:
            if _skip(f.name, excl_files, excl_types, patterns):
                continue
            yield str(f.path)


def generate_documentation(
        directory: str,
        output_filepath: str,
        *,
        exclude_tests: bool = False,
        user_excludes: Iterable[str] | None = None,
        only: str | None = None,
        specific_file: str | None = None,
        fast_tree_only: bool = False,
        status_cb: Callable[[str, Any], None] | None = None
) -> None:
    if specific_file:
        specific_file_path = Path(specific_file).resolve()
        if not specific_file_path.exists():
            logging.error("Specified file does not exist: %s", specific_file)
            return

        with open(output_filepath, "w", encoding="utf-8") as md:
            md.write(f"## Documentation for {specific_file}\n\n")
            try:
                with open(specific_file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                _dump_one(md, str(specific_file_path.parent), str(specific_file_path), text)
            except Exception as e:
                logging.error("Failed to process file %s: %s", specific_file, e)
        logging.info("Documentation saved → %s", output_filepath)
        return

    # Build exclusions
    dirs = list(DEFAULT_EXCLUDED_DIRECTORIES)
    files = list(DEFAULT_EXCLUDED_FILES)
    patterns = list(DEFAULT_EXCLUDED_FILE_PATTERNS)
    types = set(DEFAULT_EXCLUDED_FILE_TYPES)

    if exclude_tests:
        patterns.append("*_test.*")
    if user_excludes:
        dirs += [os.path.basename(p.strip("/\\")) for p in user_excludes]
        files += [os.path.basename(p.strip("/\\")) for p in user_excludes]

    excluded_dirs, excluded_files, compiled_patterns = normalize_exclusions(dirs, files, patterns)
    roots: list[Path] = []
    if only:
        for p in (s.strip() for s in only.split(",")):
            ab = Path(p).expanduser()
            try:
                resolved = ab.resolve(strict=True)
                roots.append(resolved)
            except FileNotFoundError:
                logging.warning(f"[recon] Skipping missing path: {ab}")
    if not roots:
        roots = [Path(directory)]
    # Write output
    with open(output_filepath, "w", encoding="utf-8") as md:
        md.write(f"## Project Directory Structure of {directory}\n\n")
        md.write(generate_directory_tree(
            directory=directory,
            excluded_dirs=list(excluded_dirs),
            excluded_files=list(excluded_files),
            excluded_patterns=patterns,
        ) + "\n\n")

        if fast_tree_only:
            logging.info("Fast tree‑only mode completed.")
            return

        # Walk and dump files
        all_files = list(_iter_files(list(roots), excluded_dirs, excluded_files, types, compiled_patterns))
        total = len(all_files)
        if status_cb:
            status_cb("walk", total)

        if status_cb:
            status_cb("write", None)

        for idx, path in enumerate(all_files, 1):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
                _dump_one(md, str(directory), str(path), text)
                if status_cb:
                    status_cb("read", (idx, total))
            except Exception:
                continue

    logging.info("Documentation saved → %s", output_filepath)