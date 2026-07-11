"""Unit test conftest for SpacetimeCRM.

Replaces slowapi limiter with no-op, mocks STDB HTTP client.
Must execute at import time (before any test module is collected).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add server directory to path
_server_dir = str(Path(__file__).resolve().parent.parent.parent)
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

# Ensure venv site-packages is accessible
_venv_site = str(Path(_server_dir) / '.venv' / 'lib' / 'python3.11' / 'site-packages')
if _venv_site not in sys.path:
    sys.path.insert(0, _venv_site)

import os
from unittest.mock import MagicMock, AsyncMock

os.environ.setdefault('STDB_HOST', 'localhost')
os.environ.setdefault('STDB_PORT', '3001')
os.environ.setdefault('STDB_DB', 'spacetime-crm')
os.environ.setdefault('JWT_SECRET', 'test-secret-12345678901234567890123456789012')
os.environ.setdefault('JWT_ALGORITHM', 'HS256')
os.environ.setdefault('JWT_EXPIRE_HOURS', '8')
os.environ.setdefault('APP_URL', 'http://localhost:8723')
os.environ.setdefault('STRUCTURED_LOGGING', 'false')
os.environ.setdefault('CORS_ORIGIN', 'http://localhost:5185')
os.environ.setdefault('STRIPE_SECRET_KEY', '')
os.environ.setdefault('STRIPE_WEBHOOK_SECRET', '')

# Replace slowapi limiter with no-op
class _NoopLimiter:
    def limit(self, *a, **kw):
        def dec(f): return f
        return dec

import rate_limit
rate_limit.limiter = _NoopLimiter()

# Mock STDB HTTP client
import client as _client_mod
_mc = MagicMock()
_mc.post = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: []))
_mc.get = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: {}))
_mc.is_closed = False
_client_mod._shared_client = _mc

import pytest
from starlette.testclient import TestClient as _TestClient


@pytest.fixture(scope="session")
def app():
    from main import app
    app.state.limiter = _NoopLimiter()
    return app


@pytest.fixture(scope="function")
def client(app):
    with _TestClient(app, base_url="http://localhost") as c:
        yield c
