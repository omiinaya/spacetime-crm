"""Unit tests for server/business_hours.py.

Tests settings loading, saving, updating, and default day population
for the JSON-based business hours configuration.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

DAY_NAMES = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

DEFAULT_HOURS = {
    "monday": {"enabled": True, "open": "09:00", "close": "18:00"},
    "tuesday": {"enabled": True, "open": "09:00", "close": "18:00"},
    "wednesday": {"enabled": True, "open": "09:00", "close": "18:00"},
    "thursday": {"enabled": True, "open": "09:00", "close": "18:00"},
    "friday": {"enabled": True, "open": "09:00", "close": "18:00"},
    "saturday": {"enabled": False, "open": "10:00", "close": "14:00"},
    "sunday": {"enabled": False, "open": "10:00", "close": "14:00"},
}


@pytest.fixture(autouse=True)
def _patch_path():
    """Replace SETTINGS_PATH with a temporary file for each test."""
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    import business_hours

    orig = business_hours.SETTINGS_PATH
    business_hours.SETTINGS_PATH = Path(p)
    yield
    business_hours.SETTINGS_PATH = orig
    if Path(p).exists():
        Path(p).unlink()


class TestLoadSettings:
    """_load_settings() — reading from the JSON file."""

    def test_load_no_file_returns_none(self) -> None:
        from business_hours import _load_settings

        # No file was created by fixture, so path doesn't exist
        result = _load_settings()
        assert result is None

    def test_load_missing_file_returns_none(self) -> None:
        """When SETTINGS_PATH does not exist on disk, _load_settings returns None."""
        from business_hours import _load_settings
        from business_hours import SETTINGS_PATH

        # Remove the temp file so the path truly doesn't exist
        SETTINGS_PATH.unlink()
        assert not SETTINGS_PATH.exists()
        result = _load_settings()
        assert result is None

    def test_load_valid_json(self) -> None:
        from business_hours import _load_settings
        from business_hours import SETTINGS_PATH

        data = {"monday": {"enabled": True, "open": "08:00", "close": "17:00"}}
        SETTINGS_PATH.write_text(json.dumps(data))
        result = _load_settings()
        assert result == data

    def test_load_returns_parsed_dict(self) -> None:
        from business_hours import _load_settings
        from business_hours import SETTINGS_PATH

        data = {"monday": {"enabled": True, "open": "09:00", "close": "18:00"}}
        SETTINGS_PATH.write_text(json.dumps(data))
        result = _load_settings()
        assert isinstance(result, dict)

    def test_load_parse_error_returns_none(self) -> None:
        from business_hours import _load_settings
        from business_hours import SETTINGS_PATH

        SETTINGS_PATH.write_text("invalid json content")
        with patch("business_hours.logger"):
            result = _load_settings()
            assert result is None

    def test_load_empty_file_returns_none(self) -> None:
        from business_hours import _load_settings
        from business_hours import SETTINGS_PATH

        SETTINGS_PATH.write_text("")
        with patch("business_hours.logger"):
            result = _load_settings()
            assert result is None


class TestSaveSettings:
    """_save_settings() — writing to the JSON file."""

    def test_save_writes_json(self) -> None:
        from business_hours import _save_settings
        from business_hours import SETTINGS_PATH

        data = {"monday": {"enabled": True, "open": "08:00", "close": "17:00"}}
        _save_settings(data)
        assert SETTINGS_PATH.exists()
        loaded = json.loads(SETTINGS_PATH.read_text())
        assert loaded["monday"] == {"enabled": True, "open": "08:00", "close": "17:00"}

    def test_save_round_trip(self) -> None:
        from business_hours import _load_settings
        from business_hours import _save_settings

        data = {"friday": {"enabled": True, "open": "10:00", "close": "19:00"}}
        _save_settings(data)
        loaded = _load_settings()
        assert loaded is not None
        assert loaded["friday"] == {"enabled": True, "open": "10:00", "close": "19:00"}

    def test_save_fills_missing_days(self) -> None:
        """_save_settings should fill missing days with defaults."""
        from business_hours import _save_settings
        from business_hours import SETTINGS_PATH

        _save_settings({"monday": {"enabled": True, "open": "08:00", "close": "17:00"}})
        loaded = json.loads(SETTINGS_PATH.read_text())
        for day in DAY_NAMES:
            assert day in loaded
        # Monday was provided
        assert loaded["monday"] == {"enabled": True, "open": "08:00", "close": "17:00"}
        # Other days should have defaults
        for day in DAY_NAMES[1:]:
            assert loaded[day] == DEFAULT_HOURS[day]

    def test_save_indents_json(self) -> None:
        """Saved JSON should be indented for readability."""
        from business_hours import _save_settings
        from business_hours import SETTINGS_PATH

        _save_settings({"monday": {"enabled": True, "open": "09:00", "close": "18:00"}})
        content = SETTINGS_PATH.read_text()
        assert "  " in content  # basic indentation check
        parsed = json.loads(content)
        assert parsed["monday"] == {"enabled": True, "open": "09:00", "close": "18:00"}

    def test_save_replaces_existing_content(self) -> None:
        """Saving should overwrite existing file content."""
        from business_hours import _save_settings
        from business_hours import SETTINGS_PATH

        _save_settings({"first": {"enabled": True, "open": "09:00", "close": "17:00"}})
        _save_settings(
            {"second": {"enabled": False, "open": "10:00", "close": "16:00"}}
        )
        loaded = json.loads(SETTINGS_PATH.read_text())
        assert "first" not in loaded


class TestGetSettings:
    """get_settings() — public API for reading settings."""

    def test_get_settings_no_file_returns_none(self) -> None:
        from business_hours import get_settings

        result = get_settings()
        assert result is None

    def test_get_settings_returns_saved(self) -> None:
        from business_hours import get_settings
        from business_hours import SETTINGS_PATH

        data = {"tuesday": {"enabled": True, "open": "07:00", "close": "15:00"}}
        SETTINGS_PATH.write_text(json.dumps(data))
        result = get_settings()
        assert result == data


class TestUpdateSettings:
    """update_settings() — public API for saving settings."""

    def test_update_settings_returns_dict(self) -> None:
        from business_hours import update_settings

        result = update_settings(
            {"monday": {"enabled": True, "open": "09:00", "close": "18:00"}}
        )
        assert isinstance(result, dict)

    def test_update_settings_contains_all_days(self) -> None:
        """Result should include all 7 days of the week."""
        from business_hours import update_settings

        result = update_settings({})
        for day in DAY_NAMES:
            assert day in result

    def test_update_settings_preserves_provided_data(self) -> None:
        from business_hours import update_settings

        result = update_settings(
            {"monday": {"enabled": True, "open": "10:00", "close": "19:00"}}
        )
        assert result["monday"]["enabled"] is True
        assert result["monday"]["open"] == "10:00"
        assert result["monday"]["close"] == "19:00"

    def test_update_settings_fills_unprovided_days_with_disabled_defaults(self) -> None:
        """Days not in the update data should get disabled defaults (enabled=False)."""
        from business_hours import update_settings

        result = update_settings(
            {"monday": {"enabled": True, "open": "09:00", "close": "18:00"}}
        )
        for day in ["tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            assert result[day]["enabled"] is False
            assert result[day]["open"] == "09:00"
            assert result[day]["close"] == "18:00"

    def test_update_settings_handles_partial_day_data(self) -> None:
        """Partial data for a day should fill missing fields with defaults."""
        from business_hours import update_settings

        result = update_settings({"monday": {"enabled": True}})
        assert result["monday"]["enabled"] is True
        assert result["monday"]["open"] == "09:00"
        assert result["monday"]["close"] == "18:00"

    def test_update_settings_handles_empty_day_data(self) -> None:
        from business_hours import update_settings

        result = update_settings({"monday": {}})
        assert result["monday"]["enabled"] is False
        assert result["monday"]["open"] == "09:00"
        assert result["monday"]["close"] == "18:00"

    def test_update_settings_persists_to_file(self) -> None:
        from business_hours import update_settings
        from business_hours import _load_settings

        update_settings(
            {"wednesday": {"enabled": True, "open": "08:00", "close": "16:00"}}
        )
        loaded = _load_settings()
        assert loaded is not None
        assert loaded["wednesday"]["open"] == "08:00"

    def test_update_settings_boolean_coercion(self) -> None:
        """enabled should be coerced to bool."""
        from business_hours import update_settings

        result = update_settings({"monday": {"enabled": 1}})
        assert result["monday"]["enabled"] is True

        result = update_settings({"tuesday": {"enabled": 0}})
        assert result["tuesday"]["enabled"] is False

    def test_update_settings_string_coercion(self) -> None:
        """open and close should be coerced to str."""
        from business_hours import update_settings

        result = update_settings({"monday": {"open": 8, "close": 17}})
        assert result["monday"]["open"] == "8"
        assert result["monday"]["close"] == "17"

    def test_update_settings_with_custom_days(self) -> None:
        """Multiple days can be updated in a single call."""
        from business_hours import update_settings

        data = {
            "monday": {"enabled": True, "open": "09:00", "close": "17:00"},
            "friday": {"enabled": True, "open": "09:00", "close": "16:00"},
        }
        result = update_settings(data)
        assert result["monday"]["close"] == "17:00"
        assert result["friday"]["close"] == "16:00"

    def test_update_settings_ignores_unknown_days(self) -> None:
        """Keys that aren't valid day names should be ignored."""
        from business_hours import update_settings

        result = update_settings({"unknown_day": {"enabled": True}})
        assert "unknown_day" not in result
        for day in DAY_NAMES:
            assert day in result
