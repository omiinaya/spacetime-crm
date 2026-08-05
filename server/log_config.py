"""Structured JSON logging configuration for SpacetimeCRM.

Provides a standardized JSON log format for production use.
In dev mode, logs remain human-readable via the console handler.
"""

import os
import json
import logging
import sys
from datetime import datetime, timezone

LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()
# Enable JSON logging for production (structured logs)
STRUCTURED = os.getenv("STRUCTURED_LOGGING", "false").lower() in ("true", "1", "yes")


class JsonFormatter(logging.Formatter):
    """Format log records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "extra_fields"):
            log_entry.update(record.extra_fields)
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


def configure_logging() -> None:
    """Configure structured logging for the app. Sets up root logger once.

    In production (STRUCTURED_LOGGING=true), outputs JSON to stderr.
    In dev, outputs colored text to stderr.
    Call once at application startup (in main.py).
    """
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logger.level)

    if STRUCTURED:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    logger.addHandler(handler)


def get_uvicorn_log_config() -> dict:
    """Return a uvicorn-compatible logging config dict.

    When STRUCTURED_LOGGING is true, both uvicorn.access and uvicorn.error
    loggers use the JSON formatter. Otherwise, standard text format.
    This config is passed to ``uvicorn.run(log_config=...)`` so that
    uvicorn's own loggers produce the same format as the app loggers.
    """
    formatter_name = "json" if STRUCTURED else "text"
    text_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "log_config.JsonFormatter",
            },
            "text": {
                "format": text_fmt,
                "datefmt": datefmt,
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": formatter_name,
                "stream": "ext://sys.stderr",
            },
            "access": {
                "class": "logging.StreamHandler",
                "formatter": formatter_name,
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": LOG_LEVEL, "propagate": False},
            "uvicorn.error": {"handlers": ["default"], "level": LOG_LEVEL, "propagate": False},
            "uvicorn.access": {"handlers": ["access"], "level": LOG_LEVEL, "propagate": False},
        },
        "root": {
            "handlers": ["default"],
            "level": LOG_LEVEL,
        },
    }
