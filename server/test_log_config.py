"""
Tests for server/log_config.py.

Tests JSON structured logging formatter and configuration.
"""

from __future__ import annotations

import json
import logging
import sys

from server.log_config import LOG_LEVEL, JsonFormatter, configure_logging


class TestLogConfig:
    """Test suite for log_config.py."""

    def test_json_formatter_output(self):
        """JsonFormatter produces valid JSON."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Hello %s",
            args=("world",),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_logger"
        assert parsed["message"] == "Hello world"
        assert parsed["module"] == "test"
        assert parsed["function"] is None or parsed["function"] == "?"
        assert parsed["line"] == 42

    def test_json_formatter_includes_timestamp(self):
        """JsonFormatter output has an ISO timestamp."""
        formatter = JsonFormatter()
        record = logging.LogRecord("t", logging.WARNING, "f.py", 1, "msg", (), None)
        output = json.loads(formatter.format(record))
        assert "timestamp" in output
        assert "T" in output["timestamp"]

    def test_json_formatter_includes_exception(self):
        """JsonFormatter includes exception info when present."""
        formatter = JsonFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                "t",
                logging.ERROR,
                "f.py",
                1,
                "msg",
                (),
                exc_info=exc_info,
            )
        output = json.loads(formatter.format(record))
        assert "exception" in output
        assert "ValueError" in output["exception"]

    def test_configure_logging_sets_level(self):
        """configure_logging sets the correct log level."""
        logger = configure_logging("test_logger_cfg")
        assert logger.level == getattr(logging, LOG_LEVEL, logging.INFO)

    def test_configure_logging_clears_existing_handlers(self):
        """configure_logging removes existing handlers first."""
        logger = logging.getLogger("test_handler_clear")
        logger.addHandler(logging.NullHandler())
        configure_logging("test_handler_clear")
        assert len(logger.handlers) == 1

    def test_configure_logging_adds_stream_handler(self):
        """configure_logging adds a StreamHandler."""
        logger = configure_logging("test_stream_handler")
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "StreamHandler" in handler_types

    def test_configure_logging_returns_logger(self):
        """configure_logging returns the configured logger."""
        logger = configure_logging("test_return_value")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_return_value"
