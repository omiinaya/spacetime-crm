"""
Integration tests for server/client.py.

Requires a live SpacetimeCRM server at http://localhost:8723.
Skips gracefully when the server is unavailable.
"""

from __future__ import annotations

import httpx
import pytest

# Check server availability at module level
try:
    _resp = httpx.get("http://localhost:8723/api/health", timeout=3)
    _SERVER_OK = _resp.status_code < 500
except Exception:
    _SERVER_OK = False

if not _SERVER_OK:
    pytest.skip(
        "CRM server not available -- skipping integration tests",
        allow_module_level=True,
    )

# Import all unit test classes
from server.test_client import *  # noqa: F403
