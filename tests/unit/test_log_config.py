"""Tests for log_config module (JSON formatter and uvicorn config)."""

import json
import logging
from unittest.mock import patch

from log_config import JsonFormatter, configure_logging, get_uvicorn_log_config


class TestJsonFormatter:
    def setup_method(self):
        self.formatter = JsonFormatter()

    def test_format_creates_json_line(self):
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_logger"
        assert parsed["message"] == "hello world"
        assert parsed["module"] == "test_log_config"
        assert "timestamp" in parsed
        assert "line" in parsed

    def test_format_includes_extra_fields(self):
        record = logging.LogRecord(
            name="test", level=logging.WARNING,
            pathname=__file__, lineno=5,
            msg="warn", args=(), exc_info=None,
        )
        record.extra_fields = {"request_id": "abc-123"}
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert parsed["request_id"] == "abc-123"

    def test_format_includes_exception(self):
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            record = logging.LogRecord(
                name="test", level=logging.ERROR,
                pathname=__file__, lineno=20,
                msg="error occurred", args=(), exc_info=sys.exc_info(),
            )
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert "exception" in parsed
        assert "ValueError" in parsed["exception"]

    def test_format_handles_non_string_default(self):
        record = logging.LogRecord(
            name="test", level=logging.DEBUG,
            pathname=__file__, lineno=1,
            msg="data: %s", args=({"key": "value"},),
            exc_info=None,
        )
        output = self.formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "data: {'key': 'value'}"


class TestConfigureLogging:
    def teardown_method(self):
        """Reset root logger handlers after each test."""
        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(logging.WARNING)

    def test_clears_existing_handlers(self):
        root = logging.getLogger()
        root.addHandler(logging.StreamHandler())
        configure_logging()
        assert len(root.handlers) == 1

    def test_sets_root_level_from_env(self):
        with patch("log_config.LOG_LEVEL", "DEBUG"):
            configure_logging()
            assert logging.getLogger().level == logging.DEBUG

    def test_sets_root_level_default_info(self):
        with patch("log_config.LOG_LEVEL", "INFO"):
            configure_logging()
            assert logging.getLogger().level == logging.INFO

    def test_adds_stream_handler(self):
        configure_logging()
        root = logging.getLogger()
        assert len(root.handlers) == 1
        assert isinstance(root.handlers[0], logging.StreamHandler)


class TestGetUvicornLogConfig:
    def test_returns_dict_with_version(self):
        cfg = get_uvicorn_log_config()
        assert cfg["version"] == 1
        assert cfg["disable_existing_loggers"] is False

    def test_has_formatters(self):
        cfg = get_uvicorn_log_config()
        assert "json" in cfg["formatters"]
        assert "text" in cfg["formatters"]

    def test_has_uvicorn_loggers(self):
        cfg = get_uvicorn_log_config()
        assert "uvicorn" in cfg["loggers"]
        assert "uvicorn.error" in cfg["loggers"]
        assert "uvicorn.access" in cfg["loggers"]

    def test_has_root_logger(self):
        cfg = get_uvicorn_log_config()
        # root is a top-level key in the logging dict, not in loggers
        assert "root" in cfg
        assert "handlers" in cfg["root"]

    def test_uses_text_formatter_when_not_structured(self):
        with patch("log_config.STRUCTURED", False):
            cfg = get_uvicorn_log_config()
            assert cfg["handlers"]["default"]["formatter"] == "text"
            assert cfg["handlers"]["access"]["formatter"] == "text"

    def test_json_formatter_dotted_path(self):
        cfg = get_uvicorn_log_config()
        assert cfg["formatters"]["json"]["()"] == "log_config.JsonFormatter"
