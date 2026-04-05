import logging
import os
import sys
import ctypes
from datetime import datetime
from io import TextIOWrapper
from typing import cast


def _ensure_utf8_streams() -> None:
    try:
        stdout = cast(TextIOWrapper, sys.stdout)
        stderr = cast(TextIOWrapper, sys.stderr)
        stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, ValueError):
        if os.name == "nt":
            try:
                ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            except Exception:
                pass
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def configure_logging(debug: bool = False, log_to_file: bool = False) -> None:
    _ensure_utf8_streams()

    log_level = logging.DEBUG if debug else logging.INFO
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    log_file: str | None = None
    if log_to_file:
        log_file = os.path.join(os.getcwd(), f"application_{datetime.now():%Y-%m-%d}.log")
        handlers.append(logging.FileHandler(log_file, mode="w", encoding="utf-8"))

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-7s | %(filename)s:%(lineno)d | %(message)s",
        handlers=handlers,
    )

    logging.info("Logging configured → %s", log_file if log_to_file else "console only")
