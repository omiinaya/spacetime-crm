"""Unit tests for business_hours module."""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest


@pytest.fixture(autouse=True)
def clear_business_hours_cache():
    """Ensure fresh imports for each test."""
    if 'business_hours' in sys.modules:
        del sys.modules['business_hours']


@pytest.fixture
def mock_settings_path(tmp_path):
    """Mock SETTINGS_PATH to use a temp dir."""
    import business_hours
    original_path = business_hours.SETTINGS_PATH
    test_path = tmp_path / "business_hours_settings.json"
    business_hours.SETTINGS_PATH = test_path
    yield test_path
    business_hours.SETTINGS_PATH = original_path


class TestBusinessHours:
    def test_load_settings_no_file(self, mock_settings_path):
        from business_hours import _load_settings
        assert _load_settings() is None

    def test_load_settings_valid_json(self, mock_settings_path):
        from business_hours import _load_settings
        test_data = {"monday": {"enabled": True, "open": "09:00", "close": "18:00"}}
        mock_settings_path.write_text(json.dumps(test_data))
        result = _load_settings()
        assert result == test_data

    def test_load_settings_parse_error(self, mock_settings_path):
        from business_hours import _load_settings
        mock_settings_path.write_text("not valid json")
        result = _load_settings()
        assert result is None

    def test_save_settings_fills_missing_days(self, mock_settings_path):
        from business_hours import _save_settings, DAY_NAMES
        partial = {"monday": {"enabled": True, "open": "09:00", "close": "18:00"}}
        _save_settings(partial)
        saved = json.loads(mock_settings_path.read_text())
        for day in DAY_NAMES:
            assert day in saved

    def test_get_settings_from_file(self, mock_settings_path):
        from business_hours import get_settings
        test_data = {"monday": {"enabled": True, "open": "09:00", "close": "18:00"}}
        mock_settings_path.write_text(json.dumps(test_data))
        result = get_settings()
        assert result == test_data

    def test_get_settings_no_file(self, mock_settings_path):
        from business_hours import get_settings
        mock_settings_path.unlink(missing_ok=True)
        result = get_settings()
        assert result is None

    def test_update_settings(self, mock_settings_path):
        from business_hours import update_settings, DAY_NAMES
        data = {"monday": {"enabled": True, "open": "08:00", "close": "16:00"}}
        result = update_settings(data)
        assert result["monday"]["enabled"] == True
        assert result["monday"]["open"] == "08:00"
        assert result["monday"]["close"] == "16:00"
        for day in DAY_NAMES:
            assert day in result
        assert result["tuesday"]["enabled"] == False
        assert result["tuesday"]["open"] == "09:00"

    def test_update_settings_empty_day(self, mock_settings_path):
        from business_hours import update_settings
        result = update_settings({})
        for day in ["monday", "tuesday", "wednesday"]:
            assert result[day]["enabled"] == False
            assert result[day]["open"] == "09:00"
            assert result[day]["close"] == "18:00"
