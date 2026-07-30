"""Structured JSON logging configuration for SpacetimeCRM.

Provides a standardized JSON log format for production use.
In dev mode, logs remain human-readable via the console handler.
"""

import os
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

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


def configure_logging(logger_name: Optional[str] = None) -> logging.Logger:
    """Configure structured logging for the app.

    In production (STRUCTURED_LOGGING=true), outputs JSON to stderr.
    In dev, outputs colored text to stderr.
    """
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
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
    return logger


# Configure root logger on import
configure_logging()
