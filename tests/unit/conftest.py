"""Shared fixtures for unit tests — no live backend required."""

import sys
from pathlib import Path

# Add server/ to sys.path so unit tests can import from server modules
# e.g.: from client import get_http_client
SERVER_DIR = str(Path(__file__).resolve().parents[2] / "server")
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

import pytest  # noqa: E402, F401 — keep pytest available
