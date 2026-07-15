"""Unit test conftest: replaces slowapi with no-op, provides mock STDB client.
Must execute at import time (before any test module is collected).
"""

from __future__ import annotations

import sys
from pathlib import Path

_server_dir = str(Path(__file__).resolve().parent.parent.parent)
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

_venv_site = str(Path(_server_dir) / ".venv" / "lib" / "python3.11" / "site-packages")
if _venv_site not in sys.path:
    sys.path.insert(0, _venv_site)

import os
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("STDB_HOST", "localhost")
os.environ.setdefault("STDB_PORT", "3001")
os.environ.setdefault("STDB_DB", "spacetime-crm")
os.environ.setdefault("JWT_SECRET", "test-secret-12345678901234567890123456789012")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_HOURS", "8")
os.environ.setdefault("APP_URL", "http://localhost:8723")
os.environ.setdefault("STRUCTURED_LOGGING", "false")
os.environ.setdefault("CORS_ORIGIN", "http://localhost:5185")
os.environ.setdefault("STRIPE_SECRET_KEY", "")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "")


# Replace slowapi limiter with no-op
class _NoopLimiter:
    def limit(self, *a, **kw):
        def dec(f):
            return f

        return dec


import rate_limit

rate_limit.limiter = _NoopLimiter()

# Mock STDB HTTP client — AsyncMock so await works everywhere
import client as _client_mod

_mc = AsyncMock()
_mc.is_closed = False

_default_resp = MagicMock()
_default_resp.status_code = 200
_default_resp.json.return_value = [
    {
        "rows": [["user-1", "Admin", "admin@crm.local", "admin", "t1", True, "hash", "2025-01-01"]],
        "schema": {
            "elements": [
                {"name": {"some": "id"}},
                {"name": {"some": "name"}},
                {"name": {"some": "email"}},
                {"name": {"some": "role"}},
                {"name": {"some": "tenant_id"}},
                {"name": {"some": "active"}},
                {"name": {"some": "password_hash"}},
                {"name": {"some": "created_at"}},
            ],
        },
    }
]
_mc.post = AsyncMock(return_value=_default_resp)
_mc.get = AsyncMock(return_value=MagicMock(status_code=200, json=dict))
_mc.put = AsyncMock(return_value=MagicMock(status_code=200, json=dict))
_mc.delete = AsyncMock(return_value=MagicMock(status_code=200, json=dict))
_client_mod._shared_client = _mc
_client_mod.get_http_client = lambda: _mc

# Import helpers (will use mocked client)

MOCK_USER = {
    "id": "user-1",
    "name": "Admin",
    "email": "admin@crm.local",
    "role": "admin",
    "tenant_id": "t1",
    "active": True,
}

import contextlib

import pytest
from starlette.testclient import TestClient as _TestClient


def _make_stdb_response(status: int = 200, json_data: list | None = None) -> MagicMock:
    if json_data is None:
        json_data = [
            {
                "rows": [["1"]],
                "schema": {"elements": [{"name": {"some": "ok"}}]},
            }
        ]
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    return resp


@pytest.fixture(scope="session")
def app():
    from main import app

    app.state.limiter = _NoopLimiter()
    return app


@pytest.fixture
def client(app):
    with _TestClient(app, base_url="http://localhost") as c:
        yield c


@pytest.fixture
def stdb_mock():
    return _client_mod._shared_client


@pytest.fixture
def auth_headers():
    """Return valid auth headers with admin JWT token."""
    import jwt

    from config import settings

    token = jwt.encode(
        {"sub": "user-1", "tenant_id": "t1", "role": "admin"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def configure_stdb(stdb_mock):
    def _configure(json_data: list | None = None, status: int = 200):
        resp = _make_stdb_response(status=status, json_data=json_data)
        stdb_mock.post.return_value = resp
        return stdb_mock

    return _configure


@pytest.fixture(autouse=True)
def _mock_require_role_in_routes(monkeypatch) -> None:
    """Mock require_role in route modules to bypass auth."""
    MOCK_USER = {"id": "user-1", "name": "Admin", "role": "admin", "tenant_id": "t1", "active": True}

    async def _check():
        return MOCK_USER

    def _mock(*roles):
        return _check

    # Only add mock for route modules that exist
    for mod_name in [
        "tax_rates",
        "users",
        "checklists",
        "custom_fields",
        "appointments",
        "customers",
        "dashboard",
        "estimates",
        "invoices",
        "payments",
        "payment_methods",
        "portal",
        "pos",
        "products",
        "purchase_orders",
        "recurring_invoices",
        "report_schedules",
        "settings",
        "tenants",
        "tickets",
        "webhooks",
        "export_import",
        "auth",
    ]:
        with contextlib.suppress(Exception):
            monkeypatch.setattr(f"routes.{mod_name}.require_role", _mock)
