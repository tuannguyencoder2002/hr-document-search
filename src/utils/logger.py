"""Centralized logging setup."""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger once with a consistent format."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger by name."""
    setup_logging()
    return logging.getLogger(name)
