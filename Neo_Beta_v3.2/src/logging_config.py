"""
Traceframe – logging_config.py
UTF‑8 file logging; console output only when --debug is used.
"""
import logging, os, sys, ctypes
from datetime import datetime

def _ensure_utf8_streams() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except AttributeError:                           # < Python 3.7
        if os.name == "nt":
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")

def configure_logging(debug: bool = False, log_to_file: bool = False) -> None:
    """Configure logging for the application."""
    _ensure_utf8_streams()
    log_level = logging.DEBUG if debug else logging.INFO
    handlers = [logging.StreamHandler()]

    if log_to_file:
        log_file = os.path.join(os.getcwd(), f"application_{datetime.now():%Y-%m-%d}.log")
        handlers.append(logging.FileHandler(log_file, mode="w", encoding="utf-8"))

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-7s | %(filename)s:%(lineno)d | %(message)s",
        handlers=handlers,
    )

    logging.info("Logging configured → %s", log_file if log_to_file else "console only")
