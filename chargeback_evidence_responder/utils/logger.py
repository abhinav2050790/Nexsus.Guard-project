"""Central logging setup built on loguru.

Console output is colorized and level-controlled via the
CHARGEBACK_LOG_LEVEL environment variable (INFO by default for production,
set to DEBUG during development). File output always captures DEBUG and up,
rotating at 10 MB and keeping the 5 most recent files.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from loguru import logger

PACKAGE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = PACKAGE_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"

LOG_FORMAT_CONSOLE = (
    "<green>{time:HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan> - <level>{message}</level>"
)
LOG_FORMAT_FILE = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{function}:{line} - {message}"
)


def setup_logger(level: str | None = None):
    """Reconfigure sinks and return the configured loguru logger."""
    resolved = (level or os.getenv("CHARGEBACK_LOG_LEVEL", "INFO")).upper()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger.remove()
    logger.add(sys.stderr, level=resolved, colorize=True, format=LOG_FORMAT_CONSOLE)
    logger.add(
        LOG_FILE,
        level="DEBUG",
        rotation="10 MB",
        retention=5,
        format=LOG_FORMAT_FILE,
        encoding="utf-8",
    )
    return logger


_logger = setup_logger()


def get_logger(level: str | None = None):
    """Return the shared logger; pass a level to reconfigure sinks."""
    if level is not None:
        return setup_logger(level)
    return _logger


__all__ = ["get_logger", "setup_logger", "logger"]
