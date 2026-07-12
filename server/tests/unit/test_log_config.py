"""Unit tests for log_config module."""

import json
import logging
import os
import sys
from unittest.mock import patch


class TestLogConfig:
    def test_json_formatter(self) -> None:
        from log_config import JsonFormatter

        fmt = JsonFormatter()
        record = logging.LogRecord("test", logging.INFO, "module.py", 10, "hello world", None, None)
        output = fmt.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "hello world"
        assert data["module"] == "module"
        assert "timestamp" in data

    def test_json_formatter_with_extra_fields(self) -> None:
        from log_config import JsonFormatter

        fmt = JsonFormatter()
        record = logging.LogRecord("test", logging.WARNING, "mod.py", 20, "with extra", None, None)
        record.extra_fields = {"request_id": "abc123"}
        output = fmt.format(record)
        data = json.loads(output)
        assert data["request_id"] == "abc123"
        assert data["level"] == "WARNING"

    def test_json_formatter_with_exception(self) -> None:
        from log_config import JsonFormatter

        fmt = JsonFormatter()
        try:
            msg = "test error"
            raise ValueError(msg)
        except ValueError:
            exc_info = sys.exc_info()
        record = logging.LogRecord("test", logging.ERROR, "x.py", 5, "error msg", None, exc_info)
        output = fmt.format(record)
        data = json.loads(output)
        assert data["level"] == "ERROR"
        assert "exception" in data
        assert "ValueError" in data["exception"]

    def test_configure_logging_structured(self) -> None:
        with patch.dict(
            os.environ,
            {
                "STRUCTURED_LOGGING": "true",
                "LOG_LEVEL": "DEBUG",
            },
            clear=True,
        ):
            import importlib

            import log_config

            importlib.reload(log_config)
            from log_config import configure_logging

            configure_logging()
            root = logging.getLogger()
            assert root.level == logging.DEBUG
            assert len(root.handlers) > 0

    def test_configure_logging_unstructured(self) -> None:
        with patch.dict(
            os.environ,
            {
                "STRUCTURED_LOGGING": "false",
                "LOG_LEVEL": "WARNING",
            },
            clear=True,
        ):
            import importlib

            import log_config

            importlib.reload(log_config)
            from log_config import configure_logging

            configure_logging()
            root = logging.getLogger()
            assert root.level == logging.WARNING
