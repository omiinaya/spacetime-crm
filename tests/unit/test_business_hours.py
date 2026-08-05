"""Tests for business_hours module (JSON-backed settings with defaults)."""

import json
from unittest.mock import patch, mock_open


from business_hours import (
    DEFAULT_HOURS,
    DAY_NAMES,
    _load_settings,
    _save_settings,
    get_settings,
    update_settings,
)


class TestLoadSettings:
    def test_returns_none_when_file_missing(self):
        with patch("pathlib.Path.exists", return_value=False):
            assert _load_settings() is None

    def test_returns_parsed_json_when_file_exists(self):
        data = {"monday": {"enabled": True, "open": "08:00", "close": "17:00"}}
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(data))):
                result = _load_settings()
                assert result == data

    def test_returns_none_on_corrupt_json(self):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="not json")):
                result = _load_settings()
                assert result is None


class TestSaveSettings:
    def test_fills_missing_days_with_defaults(self):
        partial = {"monday": {"enabled": True, "open": "09:00", "close": "18:00"}}
        with patch("pathlib.Path.write_text") as mock_write:
            _save_settings(partial)
            written = json.loads(mock_write.call_args[0][0])
            # All 7 days should be present
            for day in DAY_NAMES:
                assert day in written
            # Non-provided days should have defaults
            assert written["sunday"]["enabled"] is False

    def test_preserves_provided_values(self):
        data = {"monday": {"enabled": True, "open": "10:00", "close": "19:00"}}
        with patch("pathlib.Path.write_text") as mock_write:
            _save_settings(data)
            written = json.loads(mock_write.call_args[0][0])
            assert written["monday"]["open"] == "10:00"
            assert written["monday"]["close"] == "19:00"

    def test_writes_pretty_json(self):
        with patch("pathlib.Path.write_text") as mock_write:
            _save_settings({"monday": dict(DEFAULT_HOURS["monday"])})
            written = mock_write.call_args[0][0]
            parsed = json.loads(written)
            assert parsed["monday"]["enabled"] is True


class TestGetSettings:
    def test_returns_none_when_no_settings(self):
        with patch("business_hours._load_settings", return_value=None):
            assert get_settings() is None

    def test_returns_settings_when_loaded(self):
        expected = {"monday": {"enabled": True, "open": "09:00", "close": "18:00"}}
        with patch("business_hours._load_settings", return_value=expected):
            assert get_settings() == expected


class TestUpdateSettings:
    def test_updates_all_provided_days(self):
        data = {
            "monday": {"enabled": True, "open": "08:00", "close": "17:00"},
            "tuesday": {"enabled": False},
        }
        with patch("business_hours._save_settings") as mock_save:
            result = update_settings(data)
            assert result["monday"]["open"] == "08:00"
            assert result["monday"]["close"] == "17:00"
            assert result["tuesday"]["enabled"] is False
            mock_save.assert_called_once_with(result)

    def test_uses_defaults_for_missing_keys(self):
        data = {}
        with patch("business_hours._save_settings"):
            result = update_settings(data)
            assert len(result) == 7
            # update_settings creates all entries with enabled=False by default
            assert result["monday"]["enabled"] is False
            assert result["sunday"]["enabled"] is False

    def test_ensures_all_seven_days_in_result(self):
        with patch("business_hours._save_settings"):
            result = update_settings({"monday": {"enabled": True, "open": "09:00", "close": "18:00"}})
            assert set(result.keys()) == set(DAY_NAMES)
