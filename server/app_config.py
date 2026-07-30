"""App-level configuration stored as JSON on disk.

Follows the same pattern as business_hours.py for settings persistence.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parent / "config"
CONFIG_PATH = CONFIG_DIR / "app_config.json"

DEFAULT_CONFIG = {
    "revenue_target": 25000.0,
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


def update_config(data: dict) -> dict:
    """Merge data into app config and persist."""
    _ensure_dir()
    current = get_config()
    current.update(data)
    with open(CONFIG_PATH, "w") as f:
        json.dump(current, f, indent=2)
    return current
