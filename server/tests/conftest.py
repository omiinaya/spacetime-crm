"""Shared test fixtures for SpacetimeCRM API integration tests.

Requirements:
  - STDB running on localhost:3001
  - Backend running on localhost:8723 (or SERVER_URL override)

These tests exercise the live HTTP API — they mutate real STDB tables.
Run against a dedicated test database when available.
"""
import os
import json
import uuid
import pytest
import httpx

SERVER_URL = os.environ.get("CRM_TEST_SERVER", "http://localhost:8723")
ADMIN_EMAIL = os.environ.get("CRM_ADMIN_EMAIL", "admin@crm.local")
ADMIN_PW = os.environ.get("CRM_ADMIN_PW", "admin123")

# Test STDB container settings
STDB_TEST_PORT = int(os.environ.get("STDB_TEST_PORT", "3002"))
STDB_DB = os.environ.get("STDB_DB", "spacetime-crm")


def unique_suffix() -> str:
    """Return a short unique identifier for test data isolation."""
    return uuid.uuid4().hex[:12]


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def admin_token() -> str:
    """Log in as admin once per session and return the JWT."""
    resp = httpx.post(f"{SERVER_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PW,
    }, timeout=10)
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    data = resp.json()
    assert "token" in data
    return data["token"]


@pytest.fixture(scope="session")
def admin_user() -> dict:
    """Log in and return user info."""
    resp = httpx.post(f"{SERVER_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PW,
    }, timeout=10)
    assert resp.status_code == 200
    return resp.json()["user"]


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


# ── Helpers ───────────────────────────────────────────────────────


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


def create_customer(auth_headers: dict, **overrides) -> dict:
    """Create a customer and return the parsed response + ID.
    
    Uses a unique email by default to avoid collisions between test runs.
    Pass 'email' in overrides to use a specific email instead.
    """
    default_email = f"test-{unique_suffix()}@example.com"
    data = {
        "first_name": overrides.get("first_name", "Test"),
        "last_name": overrides.get("last_name", "Customer"),
        "email": overrides.get("email", default_email),
        "phone": overrides.get("phone", "555-0000"),
    }
    resp = httpx.post(
        f"{SERVER_URL}/api/customers",
        json=data,
        headers=auth_headers,
        timeout=10,
    )
    assert resp.status_code == 200, f"Customer create failed: {resp.text[:200]}"
    # Fetch it back to get the STDB-assigned ID
    r2 = httpx.get(
        f"{SERVER_URL}/api/customers",
        params={"search": data["email"]},
        headers=auth_headers,
        timeout=10,
    )
    assert r2.status_code == 200
    items = r2.json().get("customers", [])
    if items:
        return items[0]
    return {"id": "", **data}
