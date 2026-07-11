"""Unit tests for server/log_config.py - logging configuration."""
from __future__ import annotations

import sys
from pathlib import Path

_server_dir = str(Path(__file__).resolve().parent.parent.parent)
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

import os
import io
import json
import logging
from unittest.mock import patch


class TestLogConfig:
    def test_json_formatter(self):
        from log_config import JsonFormatter
        fmt = JsonFormatter()
        record = logging.LogRecord("test", logging.INFO, "module.py", 10, "hello world", None, None)
        output = fmt.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "hello world"
        assert data["module"] == "module.py"
        assert data["function"] == "?"
        assert "timestamp" in data

    def test_json_formatter_with_extra_fields(self):
        from log_config import JsonFormatter
        fmt = JsonFormatter()
        record = logging.LogRecord("test", logging.WARNING, "mod.py", 20, "with extra", None, None)
        record.extra_fields = {"request_id": "abc123"}
        output = fmt.format(record)
        data = json.loads(output)
        assert data["request_id"] == "abc123"
        assert data["level"] == "WARNING"

    def test_json_formatter_with_exception(self):
        from log_config import JsonFormatter
        fmt = JsonFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            record = logging.LogRecord("test", logging.ERROR, "x.py", 5, "error msg", None, exc_info=True)
        output = fmt.format(record)
        data = json.loads(output)
        assert data["level"] == "ERROR"
        assert "exception" in data
        assert "ValueError" in data["exception"]

    def test_configure_logging_structured(self):
        with patch.dict(os.environ, {
            "STRUCTURED_LOGGING": "true",
            "LOG_LEVEL": "DEBUG",
        }, clear=True):
            from log_config import configure_logging
            configure_logging()
            root = logging.getLogger()
            assert root.level == logging.DEBUG
            assert len(root.handlers) > 0

    def test_configure_logging_unstructured(self):
        with patch.dict(os.environ, {
            "STRUCTURED_LOGGING": "false",
            "LOG_LEVEL": "WARNING",
        }, clear=True):
            from log_config import configure_logging
            configure_logging()
            root = logging.getLogger()
            assert root.level == logging.WARNING
