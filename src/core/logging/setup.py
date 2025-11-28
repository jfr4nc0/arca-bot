"""
Centralized logging configuration with exchange_id propagation.
"""

from __future__ import annotations

import os
import sys
from contextvars import ContextVar
from typing import Optional

from loguru import logger

EXCHANGE_ID_DEFAULT = "-"
_exchange_id_var: ContextVar[str] = ContextVar(
    "exchange_id", default=EXCHANGE_ID_DEFAULT
)
_is_configured = False

LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | exchange_id={extra[exchange_id]} | "
    "{name}:{function}:{line} - {message}"
)


def _patch_record(record):
    """Inject the contextual exchange_id into every log record."""
    record["extra"]["exchange_id"] = _exchange_id_var.get(EXCHANGE_ID_DEFAULT)


def configure_logging(level: Optional[str] = None):
    """Configure Loguru once with the standard format and patcher."""
    global _is_configured
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()

    if _is_configured:
        # Allow dynamic level updates by re-adding sink when requested
        logger.remove()
    else:
        logger.remove()
        logger.configure(
            extra={"exchange_id": EXCHANGE_ID_DEFAULT}, patcher=_patch_record
        )

    logger.add(
        sys.stdout,
        level=log_level,
        format=LOG_FORMAT,
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )

    _is_configured = True


def set_exchange_id(exchange_id: Optional[str]) -> None:
    """Set the contextual exchange_id for subsequent log statements."""
    value = exchange_id or EXCHANGE_ID_DEFAULT
    _exchange_id_var.set(value)


def clear_exchange_id() -> None:
    """Clear the contextual exchange_id."""
    _exchange_id_var.set(EXCHANGE_ID_DEFAULT)


def get_exchange_id() -> str:
    """Retrieve the current contextual exchange_id."""
    return _exchange_id_var.get(EXCHANGE_ID_DEFAULT)
