"""App-level configuration stored as JSON on disk.

Follows the same pattern as business_hours.py for settings persistence.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parent / "config"
CONFIG_PATH = CONFIG_DIR / "app_config.json"

# Admin-selectable overdue reminder intervals (days after due date).
REMINDER_INTERVAL_OPTIONS = (1, 3, 7, 14)

DEFAULT_CONFIG = {
    "revenue_target": 25000.0,
    "reminder_interval_days": 3,
}


def _ensure_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def get_config() -> dict:
    """Get current app config, or defaults if not set."""
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load app config: %s", e)
        return dict(DEFAULT_CONFIG)


def _validate_reminder_interval(data: dict) -> None:
    """Validate reminder_interval_days if present — must be a positive integer.

    Raises ValueError on invalid input so callers can surface a 4xx response.
    """
    if "reminder_interval_days" not in data:
        return
    raw = data["reminder_interval_days"]
    if isinstance(raw, bool):
        raise ValueError("reminder_interval_days must be a positive integer")
    if isinstance(raw, float) and not raw.is_integer():
        raise ValueError("reminder_interval_days must be a positive integer")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(
            "reminder_interval_days must be a positive integer"
        ) from None
    if value < 1:
        raise ValueError("reminder_interval_days must be a positive integer")
    data["reminder_interval_days"] = value


def update_config(data: dict) -> dict:
    """Merge data into app config and persist."""
    _validate_reminder_interval(data)
    _ensure_dir()
    current = get_config()
    current.update(data)
    with open(CONFIG_PATH, "w") as f:
        json.dump(current, f, indent=2)
    return current
