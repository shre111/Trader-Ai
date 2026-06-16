"""
InvestIQ — shared logger.

A single console logger factory used across the module. stdout is reconfigured to
UTF-8 so the ₹ symbol never crashes logging on Windows' default cp1252 codec.
"""

import logging
import os
import sys

# Make ₹ and other non-cp1252 chars safe to print on Windows consoles.
try:  # pragma: no cover - platform dependent
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str = "investiq") -> logging.Logger:
    """Return a configured logger, namespaced under `investiq.`."""
    full_name = name if name.startswith("investiq") else f"investiq.{name}"
    logger = logging.getLogger(full_name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FMT, _DATEFMT))
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, _LEVEL, logging.INFO))
    logger.propagate = False
    return logger


# Convenience module-level logger.
logger = get_logger()
