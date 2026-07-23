"""Unit tests for server/log_config.py.

Tests the JsonFormatter class and configure_logging() function,
covering structured JSON output, dev mode, and exc_info handling.
"""

from __future__ import annotations

import json
import logging
import sys
from unittest.mock import ANY, patch

import pytest


class TestJsonFormatter:
    """Tests for the JsonFormatter class."""

    def test_format_returns_json(self) -> None:
        from log_config import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/app/server/test.py",
            lineno=42,
            msg="Hello world",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_format_includes_expected_keys(self) -> None:
        from log_config import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/app/server/test.py",
            lineno=42,
            msg="Hello world",
            args=(),
            exc_info=None,
        )
        parsed = json.loads(formatter.format(record))
        assert "timestamp" in parsed
        assert "level" in parsed
        assert "logger" in parsed
        assert "message" in parsed
        assert "module" in parsed
        assert "function" in parsed
        assert "line" in parsed

    def test_format_level_info(self) -> None:
        from log_config import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/app/server/test.py",
            lineno=42,
            msg="test",
            args=(),
            exc_info=None,
        )
        parsed = json.loads(formatter.format(record))
        assert parsed["level"] == "INFO"

    def test_format_level_error(self) -> None:
        from log_config import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/app/server/test.py",
            lineno=10,
            msg="error occurred",
            args=(),
            exc_info=None,
        )
        parsed = json.loads(formatter.format(record))
        assert parsed["level"] == "ERROR"

    def test_format_message(self) -> None:
        from log_config import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/app/server/test.py",
            lineno=1,
            msg="User %s logged in",
            args=("admin",),
            exc_info=None,
        )
        parsed = json.loads(formatter.format(record))
        assert parsed["message"] == "User admin logged in"

    def test_format_logger_name(self) -> None:
        from log_config import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="my.custom.logger",
            level=logging.INFO,
            pathname="/app/server/test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        parsed = json.loads(formatter.format(record))
        assert parsed["logger"] == "my.custom.logger"

    def test_format_module_and_function(self) -> None:
        from log_config import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/app/server/my_module.py",
            lineno=99,
            msg="test",
            args=(),
            exc_info=None,
        )
        record.funcName = "my_function"
        parsed = json.loads(formatter.format(record))
        assert parsed["module"] == "my_module"
        assert parsed["function"] == "my_function"

    def test_format_line_number(self) -> None:
        from log_config import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/app/server/test.py",
            lineno=123,
            msg="test",
            args=(),
            exc_info=None,
        )
        parsed = json.loads(formatter.format(record))
        assert parsed["line"] == 123

    def test_format_no_exc_info(self) -> None:
        """When exc_info is None, 'exception' key should not be present."""
        from log_config import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/app/server/test.py",
            lineno=1,
            msg="error",
            args=(),
            exc_info=None,
        )
        parsed = json.loads(formatter.format(record))
        assert "exception" not in parsed

    def test_format_with_exc_info(self) -> None:
        """When exc_info is set, 'exception' key should contain traceback."""
        from log_config import JsonFormatter

        formatter = JsonFormatter()
        try:
            raise ValueError("something broke")
        except ValueError:
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="/app/server/test.py",
                lineno=1,
                msg="error",
                args=(),
                exc_info=sys.exc_info(),
            )
        parsed = json.loads(formatter.format(record))
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]
        assert "something broke" in parsed["exception"]

    def test_format_with_extra_fields(self) -> None:
        """Extra fields attached via record.extra_fields should be included."""
        from log_config import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/app/server/test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        record.extra_fields = {"customer_id": 42, "tenant": "acme"}
        parsed = json.loads(formatter.format(record))
        assert parsed["customer_id"] == 42
        assert parsed["tenant"] == "acme"

    def test_format_default_str_for_non_serializable(self) -> None:
        """Non-serializable values should be converted with str()."""
        from log_config import JsonFormatter

        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/app/server/test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )
        record.extra_fields = {"obj": object()}
        parsed = json.loads(formatter.format(record))
        assert isinstance(parsed["obj"], str)


class TestConfigureLogging:
    """Tests for the configure_logging() function."""

    def test_returns_logger(self) -> None:
        from log_config import configure_logging

        logger = configure_logging("test_logger_return")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger_return"

    def test_configure_root_logger(self) -> None:
        from log_config import configure_logging

        logger = configure_logging()
        assert logger.name == "root"

    def test_configures_handler_on_logger(self) -> None:
        from log_config import configure_logging

        logger = configure_logging("test_handler_logger")
        assert len(logger.handlers) >= 1
        handler = logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream is sys.stderr

    def test_clears_existing_handlers(self) -> None:
        from log_config import configure_logging

        logger = logging.getLogger("test_clear_logger")
        logger.addHandler(logging.NullHandler())
        logger = configure_logging("test_clear_logger")
        # After configure_logging, the old NullHandler should be gone
        handler_types = [type(h).__name__ for h in logger.handlers]
        assert "NullHandler" not in handler_types

    def test_structured_mode_formatter(self) -> None:
        """In structured mode, handler should use JsonFormatter."""
        with patch("log_config.STRUCTURED", True):
            from log_config import configure_logging
            from log_config import JsonFormatter

            logger = configure_logging("test_structured")
            handler = logger.handlers[0]
            assert isinstance(handler.formatter, JsonFormatter)

    def test_dev_mode_formatter(self) -> None:
        """In dev mode, handler should use standard logging.Formatter."""
        with patch("log_config.STRUCTURED", False):
            from log_config import configure_logging

            logger = configure_logging("test_dev")
            handler = logger.handlers[0]
            assert isinstance(handler.formatter, logging.Formatter)

    def test_dev_mode_not_json_formatter(self) -> None:
        """In dev mode, formatter should NOT be JsonFormatter."""
        with patch("log_config.STRUCTURED", False):
            from log_config import configure_logging
            from log_config import JsonFormatter

            logger = configure_logging("test_dev_not_json")
            handler = logger.handlers[0]
            assert not isinstance(handler.formatter, JsonFormatter)

    def test_structured_output_valid_json(self) -> None:
        """Structured mode output should be valid JSON."""
        with patch("log_config.STRUCTURED", True):
            from log_config import configure_logging
            from log_config import JsonFormatter

            logger = configure_logging("test_structured_json")
            handler = logger.handlers[0]
            formatter = handler.formatter
            record = logging.LogRecord(
                name="test_structured_json",
                level=logging.INFO,
                pathname="/app/server/test.py",
                lineno=1,
                msg="JSON test",
                args=(),
                exc_info=None,
            )
            output = formatter.format(record)
            parsed = json.loads(output)
            assert parsed["message"] == "JSON test"
            assert parsed["level"] == "INFO"
