"""Unit tests for server/business_hours.py - business hours configuration."""
from __future__ import annotations

import sys
import json
from pathlib import Path

_server_dir = str(Path(__file__).resolve().parent.parent.parent)
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

from unittest.mock import patch, mock_open, MagicMock


class TestBusinessHours:
    def test_load_settings_no_file(self):
        from business_hours import _load_settings, SETTINGS_PATH
        with patch.object(SETTINGS_PATH, 'exists', return_value=False):
            result = _load_settings()
            assert result is None

    def test_load_settings_valid_json(self):
        from business_hours import _load_settings, SETTINGS_PATH
        test_data = {"monday": {"enabled": True, "open": "09:00", "close": "18:00"}}
        with patch.object(SETTINGS_PATH, 'exists', return_value=True):
            with patch.object(SETTINGS_PATH, 'open', mock_open(read_data=json.dumps(test_data))):
                result = _load_settings()
                assert result == test_data

    def test_load_settings_parse_error(self):
        from business_hours import _load_settings, SETTINGS_PATH
        with patch.object(SETTINGS_PATH, 'exists', return_value=True):
            with patch.object(SETTINGS_PATH, 'open', mock_open(read_data="not valid json")):
                result = _load_settings()
                assert result is None

    def test_save_settings_fills_missing_days(self):
        from business_hours import _save_settings, DAY_NAMES, SETTINGS_PATH
        partial = {"monday": {"enabled": True, "open": "09:00", "close": "18:00"}}
        with patch.object(SETTINGS_PATH, 'write_text') as mock_write:
            _save_settings(partial)
            call_args = mock_write.call_args[0][0]
            saved = json.loads(call_args)
            for day in DAY_NAMES:
                assert day in saved

    def test_get_settings_from_file(self):
        from business_hours import get_settings, SETTINGS_PATH
        test_data = {"monday": {"enabled": True, "open": "09:00", "close": "18:00"}}
        with patch.object(SETTINGS_PATH, 'exists', return_value=True):
            with patch.object(SETTINGS_PATH, 'open', mock_open(read_data=json.dumps(test_data))):
                result = get_settings()
                assert result == test_data

    def test_get_settings_no_file(self):
        from business_hours import get_settings, SETTINGS_PATH
        with patch.object(SETTINGS_PATH, 'exists', return_value=False):
            result = get_settings()
            assert result is None

    def test_update_settings(self):
        from business_hours import update_settings, DAY_NAMES, SETTINGS_PATH
        data = {"monday": {"enabled": True, "open": "08:00", "close": "16:00"}}
        with patch.object(SETTINGS_PATH, 'write_text') as mock_write:
            result = update_settings(data)
            assert result["monday"]["enabled"] == True
            assert result["monday"]["open"] == "08:00"
            assert result["monday"]["close"] == "16:00"
            for day in DAY_NAMES:
                assert day in result
            # Tuesday should be disabled by default
            assert result["tuesday"]["enabled"] == False
            assert result["tuesday"]["open"] == "09:00"

    def test_update_settings_empty_day(self):
        from business_hours import update_settings, SETTINGS_PATH
        with patch.object(SETTINGS_PATH, 'write_text'):
            result = update_settings({})
            for day in ["monday", "tuesday", "wednesday"]:
                assert result[day]["enabled"] == False
                assert result[day]["open"] == "09:00"
                assert result[day]["close"] == "18:00"
