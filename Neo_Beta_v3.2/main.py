"""
Traceframe – main.py · 2025‑05‑08
Phase‑aware ticker with live progress.
"""

from __future__ import annotations
import argparse, csv, logging, os, sys, threading, shutil, fnmatch
from datetime import datetime
from time import perf_counter_ns
from typing import Any
import pyperclip  # For clipboard functionality

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from src.file_operations  import delete_old_files
from src.documentation    import generate_documentation
from src.logging_config   import configure_logging
from src.config           import DOCUMENTATION_FILENAME, DEFAULT_EXCLUDED_DIRECTORIES, DEFAULT_EXCLUDED_FILES, DEFAULT_EXCLUDED_FILE_PATTERNS, FILES_TO_DELETE, DIRECTORIES_TO_DELETE

# ──────────────────────────────── CLI ────────────────────────────────
def _cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="traceframe",
        description="Generate Markdown docs + directory tree with live progress.")
    p.add_argument("-N", "--no-delete", action="store_true",
                   help="skip cleanup of old docs/logs")
    p.add_argument("-G", "--with-test", action="store_true",
                   help="include *_test files")
    p.add_argument("-x", "--exclude",   type=str,
                   help="comma‑separated extra paths to exclude")
    p.add_argument("-s", "--specific",  type=str,
                   help="comma‑separated explicit paths to process")
    p.add_argument("-f", "--file",      type=str,  # New argument for a specific file
                   help="specific file path to document")
    p.add_argument("--fast",    action="store_true",
                   help="tree‑only mode (skip file contents)")
    p.add_argument("--profile", action="store_true",
                   help="write traceframe_profile.csv")
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

    output_md = os.path.join(
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

    try:
        generate_documentation(
            directory=os.getcwd(),
            output_filepath=output_md,
            exclude_tests=not args.with_test,
            user_excludes=(args.exclude.split(",") if args.exclude else []),
            only=args.specific,
            specific_file=args.file,  # Pass the specific file argument
            fast_tree_only=args.fast,
            status_cb=_status_cb,          # ← live updates
        )
        marks.append(("done", perf_counter_ns()))
    finally:
        stop_evt.set()
        thr.join()

    total_ms = (marks[-1][1] - marks[0][1]) / 1e6
    print(f"\n📦  Finished in {total_ms:,.3f} ms → {os.path.basename(output_md)}")

    # Copy project_structure.md content to clipboard
    try:
        with open(output_md, "r", encoding="utf-8") as file:
            content = file.read()
            pyperclip.copy(content)
            print("📋 Project structure documentation copied to clipboard.")
    except Exception as e:
        logging.error(f"Failed to copy content to clipboard: {e}")

    # Cleanup: Remove specific files and directories from all folders
    for base_dir in [os.getcwd(), BASE_DIR]:
        for root, dirs, files in os.walk(base_dir):
            # Normalize root path
            root = os.path.normpath(root)

            # Remove specified directories
            for dir_name in dirs[:]:
                if dir_name in DIRECTORIES_TO_DELETE:
                    dir_path = os.path.join(root, dir_name)
                    shutil.rmtree(dir_path, ignore_errors=True)
                    print(f"🗑️  Removed directory {repr(dir_path)}")
                    dirs.remove(dir_name)  # Prevent further traversal into this directory

            # Remove specified files
            for file_name in files:
                file_path = os.path.normpath(os.path.join(root, file_name))
                if any(fnmatch.fnmatch(file_name, pattern) for pattern in FILES_TO_DELETE):
                    os.remove(file_path)
                    print(f"🗑️  Removed {repr(file_path)}")

    # optional CSV profile
    if args.profile:
        with open("traceframe_profile.csv", "w", newline="") as fp:
            w = csv.writer(fp); base = marks[0][1]
            w.writerow(["phase", "ms_since_start"])
            for lbl, t in marks:
                w.writerow([lbl, (t-base)/1e6])
        logging.info("Wrote traceframe_profile.csv")

# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()