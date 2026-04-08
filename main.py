"""
recon – main.py
Reconnaissance on your codebase. Phase‑aware ticker with live progress.
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import logging
import os
import shutil
import sys
import threading
from datetime import datetime
from time import perf_counter_ns
from typing import Any
from pathlib import Path

import pyperclip  # For clipboard functionality

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from src.config import (DIRECTORIES_TO_DELETE, DOCUMENTATION_FILENAME,
                        FILES_TO_DELETE)
from src.documentation import generate_documentation
from src.file_operations import delete_old_files, fuzzy_find
from src.manifest import generate_manifest, scaffold_identities
from src.logging_config import configure_logging


# ──────────────────────────────── CLI ────────────────────────────────
def _cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="recon",
        description="Reconnaissance on your codebase — Markdown docs + directory tree with live progress.")
    p.add_argument("-N", "--no-delete", action="store_true",
                   help="skip cleanup of old docs/logs")
    p.add_argument("-G", "--with-test", action="store_true",
                   help="include *_test files")
    p.add_argument("-x", "--exclude",   type=str,
                   help="comma-separated file or folder names to exclude (by base name)")
    p.add_argument("-s", "--specific",
        help="Comma-separated path *suffixes* to document. "
            "Examples: -s db  |  -s managers/db  |  -s kratos/infra")
    p.add_argument("-f", "--file",      type=str,
                   help="specific file path to document")
    p.add_argument("--auto-deps", type=str,
               help="main file to analyze and auto-populate dependencies")
    p.add_argument("-o", "--output", type=str,
                   help="custom output file path (default: project_structure_{timestamp}.md)")
    p.add_argument("--no-clipboard", action="store_true",
                   help="skip copying output to clipboard")
    p.add_argument("--manifest", action="store_true",
                   help="extract file identity (frontmatter, docstrings, comments) into a manifest")
    p.add_argument("--scaffold", action="store_true",
                   help="generate .recon/identities.yaml with TODO entries for files lacking identity")
    p.add_argument("--fast",    action="store_true",
                   help="tree‑only mode (skip file contents)")
    p.add_argument("--profile", action="store_true",
                   help="write recon_profile.csv")
    p.add_argument("--debug",   action="store_true",
                   help="verbose console logging")
    return p.parse_args()

# ─────────────────────────── ticker helpers ──────────────────────────
_status = "starting…"          # shared; safe thanks to the GIL

def _ticker(stop: threading.Event, t0: int) -> None:
    if not sys.stdout.isatty():
        return
    while not stop.is_set():
        ms = (perf_counter_ns() - t0) / 1e6
        print(f"\r⏱  {ms:9.3f} ms  {_status:<35}", end="", flush=True)
        stop.wait(0.2)

def _status_cb(label: str, data: Any) -> None:
    """Receive phase updates from documentation.py."""
    global _status
    if label == "walk":
        _status = f"scanned {data} files"
    elif label == "read":
        idx, total = data
        pct = idx * 100 / total if total else 100
        _status = f"reading {idx}/{total}  ({pct:3.0f} %)"
    elif label == "write":
        _status = "writing output…"
    else:
        _status = label

# ─────────────────────────────── main ────────────────────────────────
def main() -> None:
    args = _cli()

    # delete old docs/logs BEFORE a new log handler is opened
    if not args.no_delete:
        delete_old_files(os.getcwd())

    # Configure logging: only create a log file if --debug is enabled
    configure_logging(debug=args.debug, log_to_file=args.debug)

    output_md = args.output or os.path.join(
        os.getcwd(),
        DOCUMENTATION_FILENAME.format(timestamp=datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    )

    marks: list[tuple[str, int]] = []
    marks.append(("start", perf_counter_ns()))

    stop_evt = threading.Event()
    thr = threading.Thread(target=_ticker,
                           args=(stop_evt, marks[0][1]),
                           daemon=True)
    thr.start()
    if args.auto_deps:
        from src.file_operations import resolve_import_dependencies
        deps = resolve_import_dependencies(args.auto_deps)
        specific_paths = [os.path.abspath(dep) for dep in deps if os.path.exists(dep)]
        args.specific = ",".join(specific_paths)
    try:
        # Parse --specific paths early to ensure correctness
        specific_paths = []
        if args.specific:
            for raw in args.specific.split(","):
                q = raw.strip()
                if not q:
                    continue

                # 1️⃣ first try “exact path” (relative or absolute)
                cand = Path(q)
                if not cand.is_absolute():
                    cand = Path.cwd() / cand
                if cand.exists():
                    specific_paths.append(str(cand.resolve()))
                    continue

                # 2️⃣ fallback → fuzzy search
                matches = fuzzy_find(q, Path.cwd())
                if len(matches) == 1:
                    specific_paths.append(str(matches[0].resolve()))
                elif len(matches) > 1:
                    print(f"\n❗  Ambiguous -s '{q}':")
                    for idx, m in enumerate(matches, 1):
                        print(f"  {idx:>2}. {m.relative_to(Path.cwd())}")
                    print("👉  Please rerun with a longer suffix, e.g. recon -s managers/db")
                    sys.exit(1)
                else:
                    logging.warning(f"[recon] No match for '{q}'")

        if args.specific and not specific_paths:
            logging.error("No valid paths in --specific; aborting.")
            sys.exit(1)

        if args.debug:
            print("🧭 Specific Paths Used:", specific_paths or ["<entire directory>"])

        if args.scaffold:
            sidecar_path = scaffold_identities(
                directory=os.getcwd(),
                exclude_tests=not args.with_test,
                user_excludes=(args.exclude.split(",") if args.exclude else []),
                only=",".join(specific_paths) if specific_paths else None,
                status_cb=_status_cb,
            )
            print(f"\n📝  Scaffolded → {sidecar_path}")
            print("    Fill in the TODO entries, then run --manifest to see the result.")
        elif args.manifest:
            generate_manifest(
                directory=os.getcwd(),
                output_filepath=output_md,
                exclude_tests=not args.with_test,
                user_excludes=(args.exclude.split(",") if args.exclude else []),
                only=",".join(specific_paths) if specific_paths else None,
                status_cb=_status_cb,
            )
        else:
            generate_documentation(
                directory=os.getcwd(),
                output_filepath=output_md,
                exclude_tests=not args.with_test,
                user_excludes=(args.exclude.split(",") if args.exclude else []),
                only=",".join(specific_paths) if specific_paths else None,
                specific_file=args.file,
                fast_tree_only=args.fast,
                status_cb=_status_cb,
            )
        marks.append(("done", perf_counter_ns()))
    finally:
        stop_evt.set()
        thr.join()

    total_ms = (marks[-1][1] - marks[0][1]) / 1e6
    print(f"\n📦  Finished in {total_ms:,.3f} ms → {os.path.basename(output_md)}")

    # Copy output to clipboard unless --no-clipboard
    if not args.no_clipboard:
        try:
            with open(output_md, "r", encoding="utf-8") as file:
                content = file.read()
                pyperclip.copy(content)
                print("📋 Project structure documentation copied to clipboard.")
        except Exception as e:
            logging.error(f"Failed to copy content to clipboard: {e}")

    # Cleanup: Remove recon's own build artifacts (not the target project)
    for root, dirs, files in os.walk(BASE_DIR):
        root = os.path.normpath(root)

        for dir_name in dirs[:]:
            if dir_name in DIRECTORIES_TO_DELETE:
                dir_path = os.path.join(root, dir_name)
                shutil.rmtree(dir_path, ignore_errors=True)
                print(f"🗑️  Removed directory {repr(dir_path)}")
                dirs.remove(dir_name)

        for file_name in files:
            file_path = os.path.normpath(os.path.join(root, file_name))
            if any(fnmatch.fnmatch(file_name, pattern) for pattern in FILES_TO_DELETE):
                os.remove(file_path)
                print(f"🗑️  Removed {repr(file_path)}")

    # optional CSV profile
    if args.profile:
        with open("recon_profile.csv", "w", newline="") as fp:
            w = csv.writer(fp); base = marks[0][1]
            w.writerow(["phase", "ms_since_start"])
            for lbl, t in marks:
                w.writerow([lbl, (t-base)/1e6])
        logging.info("Wrote recon_profile.csv")

# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
