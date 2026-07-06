"""Shared test fixtures for SpacetimeCRM API integration tests.

Requirements:
  - STDB running on localhost:3001
  - Backend running on localhost:8723 (or SERVER_URL override)

These tests exercise the live HTTP API — they mutate real STDB tables.
Every test session gets a unique session_suffix so data from different
sessions (parallel/sequential) never collides. Created entities are
tracked and cleaned up at session end.
"""
import os
import json
import uuid
import pytest
import httpx

SERVER_URL = os.environ.get("CRM_TEST_SERVER", "http://localhost:8723")
ADMIN_EMAIL = os.environ.get("CRM_ADMIN_EMAIL", "admin@crm.local")
ADMIN_PW = os.environ.get("CRM_ADMIN_PW", "PLACEHOLDER_ADMIN_PW")

# Test STDB container settings (used by test helpers for direct SQL lookups)
STDB_HOST = os.environ.get("STDB_HOST", "localhost")
STDB_PORT = int(os.environ.get("STDB_TEST_PORT", os.environ.get("STDB_PORT", "3002")))
STDB_DB = os.environ.get("STDB_DB", "spacetime-crm")
STDB_SQL_URL = f"http://{STDB_HOST}:{STDB_PORT}/v1/database/{STDB_DB}/sql"


def _stdb_sql(query: str) -> list[dict]:
    """Run raw SQL against the STDB test instance and return rows.

    Used by test helpers to look up entities by unique identifiers
    when the REST API doesn't support search/filter for that entity type.
    """
    resp = httpx.post(
        STDB_SQL_URL,
        content=query,
        headers={"Content-Type": "application/sql"},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"STDB SQL failed ({resp.status_code}): {resp.text[:200]}"
    )
    return resp.json()


def unique_suffix() -> str:
    """Return a short unique string for creating unique test entities."""
    return uuid.uuid4().hex[:8]


# ── Session-isolation tracker ──────────────────────────────────────
# Tracks entities created during a test session so they can be cleaned
# up at session end. Keyed by entity type for optional targeted cleanup.

_CREATED_ENTITIES: dict[str, list[str]] = {}


def _track_entity(entity_type: str, entity_id: str) -> None:
    """Record an entity ID for cleanup at session end."""
    _CREATED_ENTITIES.setdefault(entity_type, []).append(entity_id)


def _cleanup_tracked(auth_headers: dict, session_suffix: str) -> int:
    """Delete all entities tracked during this session.

    Deletes by entity type in dependency order (children before parents).
    Returns count of deletions attempted.
    """
    # Delete in reverse-dependency order (children first)
    order = ["webhook_subscription", "payment", "adjustment", "pos_line_item",
             "customer", "invoice", "estimate", "purchase_order", "appointment",
             "product", "checklist_template", "tax_rate", "user",
             "recurring_invoice_rule", "custom_field_definition", "counter_sale",
             "ticket"]
    count = 0
    for etype in reversed(order):
        ids = _CREATED_ENTITIES.pop(etype, [])
        for eid in ids:
            try:
                resp = httpx.delete(
                    f"{SERVER_URL}/api/{etype}/{eid}",
                    headers=auth_headers, timeout=10,
                )
                if resp.status_code < 500:
                    count += 1
            except Exception:
                pass
    return count


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def session_suffix() -> str:
    """A unique identifier shared across the entire test session.

    Use this as a prefix when creating entities so all data from one
    session run can be distinguished from data left by previous runs.
    Example: email=f"test-{session_suffix}-{unique_suffix()}@example.com"
    """
    return uuid.uuid4().hex[:12]


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


@pytest.fixture(scope="session")
def auth_headers_session(admin_token) -> dict:
    """Session-scoped bearer auth header dict for cleanup operations."""
    return {"Authorization": f"Bearer {admin_token}"}


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


# ── Session cleanup fixture ──────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def _session_cleanup(request, session_suffix: str, auth_headers_session: dict):
    """Clean up all entities created during this test session.

    Runs once at session end. Cleans up tracked entities and any other
    data identifiable by session_suffix.
    """
    yield  # Session runs here

    # Cleanup after all tests complete
    _cleanup_tracked(auth_headers_session, session_suffix)


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


def create_customer(auth_headers: dict, session_suffix: str = "", **overrides) -> dict:
    """Create a customer and return the parsed response + ID.

    Uses a unique email by default to avoid collisions between test runs.
    When session_suffix is provided, it's incorporated into the email for
    easy session-level cleanup and identification.
    Pass 'email' in overrides to use a specific email instead.
    """
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
        result = items[0]
        _track_entity("customer", result["id"])
        return result
    return {"id": "", **data}


# ── Settings save/restore helpers ─────────────────────────────────


def save_mail_settings(auth_headers: dict) -> dict | None:
    """Fetch current mail settings so they can be restored later."""
    try:
        resp = httpx.get(f"{SERVER_URL}/api/settings/mail", headers=auth_headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("settings")
    except Exception:
        pass
    return None


def restore_mail_settings(auth_headers: dict, settings: dict | None) -> None:
    """Restore previously saved mail settings."""
    if settings is None:
        return
    try:
        httpx.post(
            f"{SERVER_URL}/api/settings/mail",
            json={
                "smtp_host": settings.get("smtp_host", ""),
                "smtp_port": settings.get("smtp_port", 587),
                "smtp_user": settings.get("smtp_user", ""),
                "smtp_password": settings.get("smtp_password", ""),
                "smtp_from_email": settings.get("smtp_from_email", ""),
                "smtp_from_name": settings.get("smtp_from_name", ""),
                "smtp_tls": settings.get("smtp_tls", True),
            },
            headers=auth_headers, timeout=10,
        )
    except Exception:
        pass


def save_sms_settings(auth_headers: dict) -> dict | None:
    """Fetch current SMS settings so they can be restored later."""
    try:
        resp = httpx.get(f"{SERVER_URL}/api/settings/sms", headers=auth_headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("settings")
    except Exception:
        pass
    return None


def restore_sms_settings(auth_headers: dict, settings: dict | None) -> None:
    """Restore previously saved SMS settings."""
    if settings is None:
        return
    try:
        httpx.post(
            f"{SERVER_URL}/api/settings/sms",
            json={
                "twilio_account_sid": settings.get("twilio_account_sid", ""),
                "twilio_auth_token": settings.get("twilio_auth_token", ""),
                "twilio_from_number": settings.get("twilio_from_number", ""),
            },
            headers=auth_headers, timeout=10,
        )
    except Exception:
        pass


def save_user_settings(auth_headers: dict) -> dict | None:
    """Fetch current user settings so they can be restored later."""
    try:
        resp = httpx.get(f"{SERVER_URL}/api/users/settings", headers=auth_headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("settings")
    except Exception:
        pass
    return None


def restore_user_settings(auth_headers: dict, settings: dict | None) -> None:
    """Restore previously saved user settings."""
    if settings is None:
        return
    try:
        httpx.put(
            f"{SERVER_URL}/api/users/settings",
            json={
                "theme": settings.get("theme", "system"),
                "default_ticket_status": settings.get("default_ticket_status", "new"),
            },
            headers=auth_headers, timeout=10,
        )
    except Exception:
        pass


# ── SLA save/restore helpers ──────────────────────────────────────

DEFAULT_SLA_TARGETS = {"urgent": 4, "high": 24, "medium": 72, "low": 120}


def save_sla_targets(auth_headers: dict) -> dict:
    """Fetch current SLA targets and return them for later restoration."""
    try:
        resp = httpx.get(
            f"{SERVER_URL}/api/tickets/sla-settings",
            headers=auth_headers, timeout=10,
        )
        data = resp.json()
        return data.get("targets", dict(DEFAULT_SLA_TARGETS))
    except Exception:
        return dict(DEFAULT_SLA_TARGETS)


def restore_sla_targets(auth_headers: dict, targets: dict) -> None:
    """Restore SLA targets to previously saved values."""
    if not targets:
        targets = dict(DEFAULT_SLA_TARGETS)
    try:
        httpx.post(
            f"{SERVER_URL}/api/tickets/sla-settings",
            json={"targets": targets},
            headers=auth_headers, timeout=10,
        )
    except Exception:
        pass


def reset_sla_targets(auth_headers: dict) -> None:
    """Reset SLA targets back to defaults for test isolation."""
    restore_sla_targets(auth_headers, dict(DEFAULT_SLA_TARGETS))
