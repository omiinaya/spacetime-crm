"""
Unit test conftest — overrides the parent conftest's live-server fixtures.

Unit tests in this directory MUST NOT depend on a running STDB or CRM server.
The parent conftest.py at server/tests/ has session-scoped fixtures (admin_token,
isolated_tenant, etc.) that try to hit a live server and fail when it's not running.
We override them here with no-op stubs so pytest never attempts the live calls.
"""

from __future__ import annotations

import pytest


# Override every session-scoped fixture from the parent conftest that would
# try to contact a live STDB/server.  These are never used by unit tests,
# but putting them in scope prevents pytest from ever calling the real ones.
@pytest.fixture(scope="session")
def admin_token() -> str:
    return "unit-test-mock-token"


@pytest.fixture(scope="session")
def admin_user() -> dict:
    return {}


@pytest.fixture(scope="session")
def auth_headers_session() -> dict:
    return {}


@pytest.fixture(scope="session")
def session_suffix() -> str:
    return "unit-test-session"


@pytest.fixture(scope="session")
def isolated_tenant() -> dict:
    return {
        "tenant_id": "ut-tenant",
        "tenant_slug": "unit-test-tenant",
        "admin_user_id": "ut-admin",
        "admin_email": "admin@unit-test.local",
        "admin_token": "unit-test-mock-token",
    }


@pytest.fixture(scope="session")
def test_admin_token() -> str:
    return "unit-test-mock-token"


@pytest.fixture(scope="session")
def test_admin_headers() -> dict:
    return {}


@pytest.fixture(scope="session")
def test_tenant_id() -> str:
    return "ut-tenant"
