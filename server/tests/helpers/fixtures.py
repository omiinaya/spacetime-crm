"""Test fixtures — shared across all integration tests."""

from __future__ import annotations

import bcrypt
import httpx
import pytest

from tests.helpers.db import (
    _CREATED_ENTITIES,
    ADMIN_EMAIL,
    ADMIN_PW,
    SERVER_URL,
    _cleanup_by_suffix,
    _cleanup_tracked,
    _stdb_call,
    _stdb_sql,
    _track_entity,
)

# ── Session-scoped fixtures ────────────────────────────────────────


@pytest.fixture(scope="session")
def session_suffix() -> str:
    """A unique identifier shared across the entire test session.

    Use this as a prefix when creating entities so all data from one
    session run can be distinguished from data left by previous runs.
    Example: email=f"test-{session_suffix}-{unique_suffix()}@example.com"

    Before use, cleans up any leftover test data with this suffix
    (from a prior interrupted run that never cleaned up).
    """
    import uuid

    suf = uuid.uuid4().hex[:12]
    # Pre-session cleanup: remove stale data from the previous session
    # that might still match this suffix (edge case for very fast re-runs)
    _cleanup_by_suffix(suf)
    return suf


@pytest.fixture(scope="session")
def admin_token() -> str:
    """Log in as admin once per session and return the JWT."""
    resp = httpx.post(
        f"{SERVER_URL}/api/auth/login",
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PW,
        },
        timeout=10,
    )
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    data = resp.json()
    assert "token" in data
    return data["token"]


@pytest.fixture(scope="session")
def admin_user() -> dict:
    """Log in and return user info."""
    resp = httpx.post(
        f"{SERVER_URL}/api/auth/login",
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PW,
        },
        timeout=10,
    )
    assert resp.status_code == 200
    return resp.json()["user"]


@pytest.fixture(scope="session")
def auth_headers_session(admin_token) -> dict:
    """Session-scoped bearer auth header dict for cleanup operations."""
    return {"Authorization": f"Bearer {admin_token}"}


# ── Function-scoped fixtures ───────────────────────────────────────


@pytest.fixture
def client() -> httpx.Client:
    """Unauthenticated test client."""
    return httpx.Client(base_url=SERVER_URL, timeout=15)


@pytest.fixture
def auth_client(admin_token) -> httpx.Client:
    """Authenticated admin test client."""
    return httpx.Client(
        base_url=SERVER_URL,
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=15,
    )


@pytest.fixture
def auth_headers(admin_token) -> dict:
    """Bearer auth header dict for ad-hoc requests."""
    return {"Authorization": f"Bearer {admin_token}"}


# ── Isolated tenant fixtures ──────────────────────────────────────
#
# Each test session gets its own tenant with an admin user for complete
# STDB state isolation between parallel test runs. This avoids flaky tests
# when multiple test sessions run against the same STDB instance.


@pytest.fixture(scope="session")
def test_tenant_slug(session_suffix: str) -> str:
    """Unique tenant slug for this test session."""
    return f"test-tenant-{session_suffix}"


@pytest.fixture(scope="session")
def test_tenant_name(session_suffix: str) -> str:
    """Unique tenant name for this test session."""
    return f"Test Tenant {session_suffix}"


@pytest.fixture(scope="session")
def test_admin_email(session_suffix: str) -> str:
    """Unique admin email for this test session's tenant."""
    return f"admin-{session_suffix}@test.local"


@pytest.fixture(scope="session")
def test_admin_password() -> str:
    """Password for test admin users."""
    return "testadmin123"


@pytest.fixture(scope="session")
def isolated_tenant(
    test_tenant_slug: str,
    test_tenant_name: str,
    test_admin_email: str,
    test_admin_password: str,
    auth_headers_session: dict,
) -> dict:
    """
    Create an isolated tenant with an admin user for this test session.

    Returns a dict with tenant_id, admin_user_id, admin_email, admin_token.
    Cleans up the tenant at session end.
    """
    # Create tenant
    resp = httpx.post(
        f"{SERVER_URL}/api/tenants",
        json={"name": test_tenant_name, "slug": test_tenant_slug},
        headers=auth_headers_session,
        timeout=10,
    )
    assert resp.status_code == 200, f"Failed to create tenant: {resp.text}"

    # Get the tenant ID
    rows = _stdb_sql(f"SELECT * FROM tenants WHERE slug = '{test_tenant_slug}'")
    assert rows and rows[0]["rows"], f"Tenant not found: {test_tenant_slug}"
    tenant_id = rows[0]["rows"][0][0]

    # Create admin user in the new tenant
    resp = httpx.post(
        f"{SERVER_URL}/api/users",
        json={
            "name": f"test-admin-{test_tenant_slug}",
            "email": test_admin_email,
            "role": "admin",
        },
        headers=auth_headers_session,
        timeout=10,
    )
    assert resp.status_code == 200, f"Failed to create admin user: {resp.text}"

    # Get the user ID
    rows = _stdb_sql(f"SELECT * FROM user WHERE email = '{test_admin_email}'")
    assert rows and rows[0]["rows"], f"Admin user not found: {test_admin_email}"
    admin_user_id = rows[0]["rows"][0][0]

    # Add admin user to tenant
    resp = httpx.post(
        f"{SERVER_URL}/api/tenants/{tenant_id}/members",
        json={"username": f"test-admin-{test_tenant_slug}", "role": "admin"},
        headers=auth_headers_session,
        timeout=10,
    )
    assert resp.status_code == 200, f"Failed to add tenant member: {resp.text}"

    # Set password for the admin user
    hashed = bcrypt.hashpw(test_admin_password.encode(), bcrypt.gensalt()).decode()
    _stdb_call("set_user_password", [admin_user_id, hashed])

    # Log in as the test admin to get a token
    resp = httpx.post(
        f"{SERVER_URL}/api/auth/login",
        json={"email": test_admin_email, "password": test_admin_password},
        timeout=10,
    )
    assert resp.status_code == 200, f"Test admin login failed: {resp.text}"
    admin_token = resp.json()["token"]

    tenant_info = {
        "tenant_id": tenant_id,
        "tenant_slug": test_tenant_slug,
        "admin_user_id": admin_user_id,
        "admin_email": test_admin_email,
        "admin_token": admin_token,
    }

    # Track for cleanup
    _CREATED_ENTITIES.setdefault("tenant", []).append(tenant_id)
    _CREATED_ENTITIES.setdefault("user", []).append(admin_user_id)

    yield tenant_info

    # Cleanup: delete tenant (cascades to all data)
    try:
        httpx.delete(
            f"{SERVER_URL}/api/tenants/{tenant_id}",
            headers=auth_headers_session,
            timeout=10,
        )
    except Exception:
        pass


@pytest.fixture(scope="session")
def test_admin_token(isolated_tenant: dict) -> str:
    """JWT token for the isolated test admin user."""
    return isolated_tenant["admin_token"]


@pytest.fixture(scope="session")
def test_admin_headers(test_admin_token: str) -> dict:
    """Bearer auth header dict for the isolated test admin."""
    return {"Authorization": f"Bearer {test_admin_token}"}


@pytest.fixture(scope="session")
def test_tenant_id(isolated_tenant: dict) -> str:
    """Tenant ID for the isolated test tenant."""
    return isolated_tenant["tenant_id"]


# ── Session cleanup fixture ──────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def _session_cleanup(request, session_suffix: str, auth_headers_session: dict):
    """Clean up all entities created during this test session.

    Runs once at session end. Uses STDB SQL DELETE for reliable cleanup
    that doesn't depend on HTTP endpoint paths.
    """
    yield  # Session runs here

    # Cleanup after all tests complete — two strategies:
    # 1. Delete tracked entities by ID
    _cleanup_tracked(auth_headers_session, session_suffix)
    # 2. Delete any remaining entities identifiable by session_suffix
    _cleanup_by_suffix(session_suffix)


# ── Entity creation helpers ────────────────────────────────────────


def assert_ok(resp: httpx.Response, status: int = 200):
    """Assert a successful response and return parsed JSON."""
    assert resp.status_code == status, (
        f"Expected {status}, got {resp.status_code}: {resp.text[:300]}"
    )
    return resp.json()


def assert_unauthorized(resp: httpx.Response):
    """Assert a 401 or 403 response."""
    assert resp.status_code in (401, 403), (
        f"Expected 401/403, got {resp.status_code}: {resp.text[:300]}"
    )


def create_customer(auth_headers: dict, session_suffix: str = "", **overrides) -> dict:
    """Create a customer and return the parsed response + ID.

    Uses a unique email by default to avoid collisions between test runs.
    When session_suffix is provided, it's incorporated into the email for
    easy session-level cleanup and identification.
    Pass 'email' in overrides to use a specific email instead.
    """
    from tests.helpers.db import unique_suffix

    suf = unique_suffix()
    prefix = f"{session_suffix}-" if session_suffix else ""
    default_email = f"test-{prefix}{suf}@example.com"
    data = {
        "first_name": overrides.get("first_name", "Test"),
        "last_name": overrides.get("last_name", "Customer"),
        "email": overrides.get("email", default_email),
        "phone": overrides.get("phone", "555-0000"),
    }
    resp = httpx.post(
        f"{SERVER_URL}/api/customers",
        json=data,
        headers=auth_headers_session,
        timeout=10,
    )
    assert resp.status_code == 200, f"Customer create failed: {resp.text[:200]}"
    # Fetch it back to get the STDB-assigned ID
    r2 = httpx.get(
        f"{SERVER_URL}/api/customers",
        params={"search": data["email"]},
        headers=auth_headers_session,
        timeout=10,
    )
    assert r2.status_code == 200
    items = r2.json().get("customers", [])
    if items:
        result = items[0]
        _track_entity("customer", result["id"])
        return result
    return {"id": "", **data}
