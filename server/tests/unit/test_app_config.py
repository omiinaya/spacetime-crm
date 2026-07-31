"""Unit tests for server/app_config.py.

Tests the JSON-backed app-level configuration: defaults, reminder
interval validation, and persistence.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _patch_path():
    """Replace CONFIG_PATH with a temporary file for each test."""
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    import app_config

    orig = app_config.CONFIG_PATH
    app_config.CONFIG_PATH = Path(p)
    yield
    app_config.CONFIG_PATH = orig
    if Path(p).exists():
        Path(p).unlink()


class TestDefaults:
    """get_config() — default values when no file exists."""

    def test_returns_defaults_when_no_file(self) -> None:
        import app_config

        from app_config import CONFIG_PATH, DEFAULT_CONFIG, get_config

        CONFIG_PATH.unlink(missing_ok=True)
        assert get_config() == DEFAULT_CONFIG

    def test_default_has_reminder_interval(self) -> None:
        from app_config import DEFAULT_CONFIG

        assert DEFAULT_CONFIG["reminder_interval_days"] == 3
        assert DEFAULT_CONFIG["revenue_target"] == 25000.0

    def test_reminder_interval_options(self) -> None:
        from app_config import REMINDER_INTERVAL_OPTIONS

        assert REMINDER_INTERVAL_OPTIONS == (1, 3, 7, 14)

    def test_missing_file_falls_back_to_defaults(self) -> None:
        from app_config import CONFIG_PATH, get_config

        CONFIG_PATH.unlink(missing_ok=True)
        cfg = get_config()
        assert cfg["reminder_interval_days"] == 3

    def test_corrupt_file_falls_back_to_defaults(self) -> None:
        from app_config import CONFIG_PATH, get_config

        CONFIG_PATH.write_text("{not valid json")
        cfg = get_config()
        assert cfg["reminder_interval_days"] == 3
        assert cfg["revenue_target"] == 25000.0


class TestUpdateConfig:
    """update_config() — merging and persistence."""

    def test_updates_reminder_interval(self) -> None:
        from app_config import CONFIG_PATH, get_config, update_config

        result = update_config({"reminder_interval_days": 7})
        assert result["reminder_interval_days"] == 7
        # Persisted to disk
        on_disk = json.loads(CONFIG_PATH.read_text())
        assert on_disk["reminder_interval_days"] == 7
        assert get_config()["reminder_interval_days"] == 7

    def test_merges_with_existing_config(self) -> None:
        from app_config import update_config

        update_config({"revenue_target": 50000.0})
        result = update_config({"reminder_interval_days": 14})
        assert result["revenue_target"] == 50000.0
        assert result["reminder_interval_days"] == 14

    def test_accepts_numeric_string(self) -> None:
        from app_config import update_config

        result = update_config({"reminder_interval_days": "7"})
        assert result["reminder_interval_days"] == 7
        assert isinstance(result["reminder_interval_days"], int)

    def test_rejects_zero(self) -> None:
        from app_config import update_config

        with pytest.raises(ValueError):
            update_config({"reminder_interval_days": 0})

    def test_rejects_negative(self) -> None:
        from app_config import update_config

        with pytest.raises(ValueError):
            update_config({"reminder_interval_days": -3})

    def test_rejects_non_numeric(self) -> None:
        from app_config import update_config

        with pytest.raises(ValueError):
            update_config({"reminder_interval_days": "abc"})

    def test_rejects_none(self) -> None:
        from app_config import update_config

        with pytest.raises(ValueError):
            update_config({"reminder_interval_days": None})

    def test_rejects_float(self) -> None:
        from app_config import update_config

        with pytest.raises(ValueError):
            update_config({"reminder_interval_days": 3.5})

    def test_invalid_value_leaves_config_unchanged(self) -> None:
        from app_config import get_config, update_config

        update_config({"reminder_interval_days": 3})
        with pytest.raises(ValueError):
            update_config({"reminder_interval_days": 0})
        assert get_config()["reminder_interval_days"] == 3

    def test_other_keys_unaffected(self) -> None:
        from app_config import update_config

        result = update_config({"some_future_key": "x"})
        assert result["some_future_key"] == "x"
        assert result["reminder_interval_days"] == 3
