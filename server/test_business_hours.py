"""
Tests for server/business_hours.py.

Tests hours configuration, loading/saving JSON settings,
and update logic for business hours.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from server.business_hours import (
    DEFAULT_HOURS,
    DAY_NAMES,
    _load_settings,
    _save_settings,
    get_settings,
    update_settings,
)


class TestBusinessHours:
    """Test suite for business_hours.py."""

    def test_default_hours_has_all_days(self):
        """DEFAULT_HOURS contains all 7 days."""
        for day in DAY_NAMES:
            assert day in DEFAULT_HOURS

    def test_default_hours_structure(self):
        """Each day entry has enabled, open, and close keys."""
        for day in DAY_NAMES:
            entry = DEFAULT_HOURS[day]
            assert "enabled" in entry
            assert "open" in entry
            assert "close" in entry
            assert isinstance(entry["enabled"], bool)

    def test_day_names_order(self):
        """DAY_NAMES starts with monday, ends with sunday."""
        assert DAY_NAMES[0] == "monday"
        assert DAY_NAMES[-1] == "sunday"
        assert len(DAY_NAMES) == 7

    def test_default_weekdays_enabled(self):
        """Mon-Fri are enabled by default."""
        for day in DAY_NAMES[:5]:
            assert DEFAULT_HOURS[day]["enabled"] is True

    def test_default_weekends_disabled(self):
        """Sat-Sun are disabled by default."""
        for day in DAY_NAMES[5:]:
            assert DEFAULT_HOURS[day]["enabled"] is False

    def test_load_settings_no_file(self, tmp_path):
        """_load_settings returns None when file doesn't exist."""
        fake_path = tmp_path / "nonexistent.json"
        with patch("server.business_hours.SETTINGS_PATH", fake_path):
            assert _load_settings() is None

    def test_load_settings_success(self, tmp_path):
        """_load_settings returns parsed dict from file."""
        settings_file = tmp_path / "settings.json"
        test_data = {"monday": {"enabled": True, "open": "09:00", "close": "18:00"}}
        settings_file.write_text(json.dumps(test_data))
        with patch("server.business_hours.SETTINGS_PATH", settings_file):
            result = _load_settings()
            assert result == test_data

    def test_load_settings_invalid_json(self, tmp_path):
        """_load_settings returns None on JSON decode error."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json")
        with patch("server.business_hours.SETTINGS_PATH", bad_file):
            assert _load_settings() is None

    def test_save_settings_writes_all_days(self, tmp_path):
        """_save_settings ensures all 7 days are present before writing."""
        output = tmp_path / "out.json"
        with patch("server.business_hours.SETTINGS_PATH", output):
            settings = {"monday": {"enabled": True, "open": "09:00", "close": "18:00"}}
            _save_settings(settings)
            saved = json.loads(output.read_text())
            for day in DAY_NAMES:
                assert day in saved

    def test_get_settings_returns_none_when_missing(self, tmp_path):
        """get_settings returns None when no settings file exists."""
        with patch("server.business_hours.SETTINGS_PATH", tmp_path / "missing.json"):
            assert get_settings() is None

    def test_get_settings_returns_dict(self, tmp_path):
        """get_settings returns settings dict when loaded."""
        settings_file = tmp_path / "settings.json"
        test_data = {"monday": {"enabled": True, "open": "09:00", "close": "18:00"}}
        settings_file.write_text(json.dumps(test_data))
        with patch("server.business_hours.SETTINGS_PATH", settings_file):
            assert get_settings() == test_data

    def test_update_settings_partial(self, tmp_path):
        """update_settings fills missing days with defaults."""
        output = tmp_path / "out.json"
        output.write_text("{}")
        with patch("server.business_hours.SETTINGS_PATH", output):
            result = update_settings(
                {
                    "monday": {"enabled": True, "open": "10:00", "close": "19:00"},
                }
            )
            assert result["monday"]["open"] == "10:00"
            assert result["tuesday"]["enabled"] is False
            assert result["tuesday"]["open"] == "09:00"

    def test_update_settings_with_non_dict_entry(self, tmp_path):
        """update_settings handles non-dict day entry gracefully."""
        output = tmp_path / "out.json"
        output.write_text("{}")
        with patch("server.business_hours.SETTINGS_PATH", output):
            result = update_settings({"monday": "not_a_dict"})
            assert result["monday"]["enabled"] is False
            assert result["monday"]["open"] == "09:00"

    def test_update_settings_saves_to_disk(self, tmp_path):
        """update_settings writes to disk (calls _save_settings)."""
        output = tmp_path / "out.json"
        output.write_text("{}")
        with patch("server.business_hours.SETTINGS_PATH", output):
            data = {"monday": {"enabled": True, "open": "09:00", "close": "18:00"}}
            update_settings(data)
            assert output.exists()
            saved = json.loads(output.read_text())
            assert "monday" in saved
