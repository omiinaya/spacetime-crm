"""Business hours configuration for SpacetimeCRM.

Stores shop operating hours in a local JSON file.
Defaults: Mon-Fri 9am-6pm, closed Sat-Sun.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SETTINGS_PATH = Path(__file__).resolve().parent / "business_hours_settings.json"

DEFAULT_HOURS = {
    "monday":    {"enabled": True,  "open": "09:00", "close": "18:00"},
    "tuesday":   {"enabled": True,  "open": "09:00", "close": "18:00"},
    "wednesday": {"enabled": True,  "open": "09:00", "close": "18:00"},
    "thursday":  {"enabled": True,  "open": "09:00", "close": "18:00"},
    "friday":    {"enabled": True,  "open": "09:00", "close": "18:00"},
    "saturday":  {"enabled": False, "open": "10:00", "close": "14:00"},
    "sunday":    {"enabled": False, "open": "10:00", "close": "14:00"},
}

DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _load_settings() -> Optional[dict]:
    if not SETTINGS_PATH.exists():
        return None
    try:
        with open(SETTINGS_PATH) as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load business hours settings: %s", e)
        return None


def _save_settings(settings: dict) -> None:
    # Ensure all 7 days are present
    for day in DAY_NAMES:
        if day not in settings:
            settings[day] = dict(DEFAULT_HOURS[day])
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))


def get_settings() -> Optional[dict]:
    """Get current business hours, or None if default."""
    return _load_settings()


def update_settings(data: dict) -> dict:
    """Save business hours. Data should be a dict keyed by day name."""
    hours = {day: {"enabled": False, "open": "09:00", "close": "18:00"} for day in DAY_NAMES}
    for day in DAY_NAMES:
        if day in data:
            entry = data[day]
            if isinstance(entry, dict):
                hours[day] = {
                    "enabled": bool(entry.get("enabled", False)),
                    "open": str(entry.get("open", "09:00")),
                    "close": str(entry.get("close", "18:00")),
                }
    _save_settings(hours)
    return hours
