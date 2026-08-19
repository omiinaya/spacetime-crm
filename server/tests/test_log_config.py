"""Tests for structured JSON logging (ROADMAP 9A-5).

Pure unit tests — no live backend required. They exercise log_config
directly: level honoring via LOG_LEVEL / explicit level override, and
JSON emission via STRUCTURED_LOGGING / explicit structured flag.
"""
import json
import logging
import pytest

from log_config import JsonFormatter, configure_logging


class TestJsonFormatter:
    def test_emits_structured_json_line(self):
        """A log record formats as one valid JSON object with key fields."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="server/log_config.py",
            lineno=42,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )
        out = JsonFormatter().format(record)
        parsed = json.loads(out)
        assert parsed["level"] == "WARNING"
        assert parsed["logger"] == "test.logger"
        assert parsed["message"] == "hello world"
        assert parsed["line"] == 42

    def test_includes_extra_fields_when_present(self):
        """extra_fields attached to a record are merged into the JSON line."""
        record = logging.LogRecord(
            name="x", level=logging.INFO, pathname="m.py", lineno=1,
            msg="with extras", args=(), exc_info=None,
        )
        record.extra_fields = {"tenant_id": "tnt_123", "event": "audit"}
        parsed = json.loads(JsonFormatter().format(record))
        assert parsed["tenant_id"] == "tnt_123"
        assert parsed["event"] == "audit"

    def test_includes_exception_text(self):
        """Records with exc_info render an 'exception' field."""
        record = logging.LogRecord(
            name="x", level=logging.ERROR, pathname="m.py", lineno=1,
            msg="boom", args=(), exc_info=(ValueError, ValueError("bad"), None),
        )
        parsed = json.loads(JsonFormatter().format(record))
        assert "exception" in parsed
        assert "bad" in parsed["exception"]


class TestConfigureLogging:
    def test_honors_explicit_level_override(self):
        """configure_logging(level=...) sets the root logger level."""
        logger = configure_logging(level="error")
        assert logger.level == logging.ERROR

    def test_honors_explicit_structured_flag(self):
        """configure_logging(structured=True) installs the JSON formatter."""
        logger = configure_logging(level="info", structured=True)
        handler = logger.handlers[-1]
        assert isinstance(handler.formatter, JsonFormatter)

    def test_plain_formatter_when_not_structured(self):
        """Without structured, the console handler uses a text formatter."""
        logger = configure_logging(level="info", structured=False)
        handler = logger.handlers[-1]
        assert not isinstance(handler.formatter, JsonFormatter)