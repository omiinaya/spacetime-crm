"""Shared test fixtures for SpacetimeCRM API integration tests.

Requirements:
  - STDB running on localhost:3001
  - Backend running on localhost:8723 (or SERVER_URL override)

These tests exercise the live HTTP API — they mutate real STDB tables.
Every test session gets a unique session_suffix so data from different
sessions (parallel/sequential) never collides. Created entities are
tracked and cleaned up at session end via STDB SQL DELETE (not fragile
HTTP endpoint calls).
"""
import os
import json
import uuid
import time
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


def _stdb_write(query: str) -> None:
    """Run a write SQL statement (DELETE, INSERT, etc) against STDB.

    Ignores errors on DELETE — the table may not exist or be empty.
    """
    try:
        httpx.post(
            STDB_SQL_URL,
            content=query,
            headers={"Content-Type": "application/sql"},
            timeout=30,
        )
    except Exception:
        pass


def unique_suffix() -> str:
    """Return a short unique string for creating unique test entities."""
    return uuid.uuid4().hex[:8]


# ── STDB table-to-entity map for SQL-based cleanup ─────────────────
# Maps entity type names (used with _track_entity) to STDB table names.
# These tables are explicitly known to exist in the module.
_STDB_TABLES = {
    "ticket": "ticket",
    "customer": "customer",
    "invoice": "invoice",
    "payment": "payment",
    "product": "product",
    "appointment": "appointment",
    "estimate": "estimate",
    "purchase_order": "purchase_order",
    "tax_rate": "tax_rate",
    "user": "user",
    "webhook_subscription": "webhook_subscription",
    "recurring_invoice_rule": "recurring_invoice_rule",
    "report_schedule": "report_schedule",
    "checklist_template": "checklist_template",
    "custom_field_definition": "custom_field_definition",
    "counter_sale": "counter_sale",
    "adjustment": "inventory_adjustment",
    "pos_line_item": "pos_line_item",
    "saved_payment_method": "saved_payment_methods",
}

# ── Session-isolation tracker ──────────────────────────────────────
# Tracks entities created during a test session so they can be cleaned
# up at session end via STDB SQL DELETE. Keyed by entity type.

_CREATED_ENTITIES: dict[str, list[str]] = {}


def _track_entity(entity_type: str, entity_id: str) -> None:
    """Record an entity ID for cleanup at session end."""
    _CREATED_ENTITIES.setdefault(entity_type, []).append(entity_id)


def _cleanup_tracked(auth_headers: dict, session_suffix: str) -> tuple[int, int]:
    """Delete all entities tracked during this session via STDB SQL.

    Returns (success_count, fail_count). Uses STDB SQL DELETE which
    avoids the fragility of HTTP endpoint calls (wrong paths, side
    effects, missing DELETE routes).
    """
    success = 0
    fail = 0
    for etype, ids in _CREATED_ENTITIES.items():
        table = _STDB_TABLES.get(etype)
        if not table:
            continue
        for eid in ids:
            sql = f"DELETE FROM {table} WHERE id = '{eid}'"
            try:
                _stdb_write(sql)
                success += 1
            except Exception:
                fail += 1
    _CREATED_ENTITIES.clear()
    return success, fail


def _cleanup_by_suffix(session_suffix: str) -> int:
    """STDB SQL delete for entities whose IDs contain the session_suffix.

    This catches entities created by helpers that embed the session_suffix
    in their ID (e.g., device_serial contains session_suffix in ticket IDs).
    Also handles line items and notes that cascade-delete.
    """
    count = 0
    suffix = session_suffix
    # Delete in dependency-safe order (children first)
    # These are best-effort — tables may not exist or have no matching rows
    tables_order = [
        # POS child tables
        "pos_line_item",
        # Ticket child tables
        "ticket_note",
        "ticket_timer",
        "saved_payment_methods",
        # Invoice/estimate child tables
        "invoice_line_item",
        "estimate_line_item",
        "payment",
        "purchase_order_line_item",
        "inventory_adjustment",
        "appointment",
        "recurring_invoice_rule",
        "webhook_subscription",
        "report_schedule",
        "custom_field_value",
        "custom_field_definition",
        "checklist_template",
        # Main entities
        "ticket",
        "invoice",
        "estimate",
        "purchase_order",
        "counter_sale",
        "adjustment",
        "product",
        "customer",
        "tax_rate",
        "user",
    ]
    for table in tables_order:
        try:
            _stdb_write(
                f"DELETE FROM {table} "
                f"WHERE id LIKE '%{suffix}%' "
                f"OR (email IS NOT NULL AND email LIKE '%{suffix}%') "
                f"OR (vendor_name IS NOT NULL AND vendor_name LIKE '%{suffix}%') "
                f"OR (name IS NOT NULL AND name LIKE '%{suffix}%') "
                f"OR (title IS NOT NULL AND title LIKE '%{suffix}%') "
                f"OR (sku IS NOT NULL AND sku LIKE '%{suffix}%') "
                f"OR (customer_name IS NOT NULL AND customer_name LIKE '%{suffix}%')"
            )
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

    Before use, cleans up any leftover test data with this suffix
    (from a prior interrupted run that never cleaned up).
    """
    suf = uuid.uuid4().hex[:12]
    # Pre-session cleanup: remove stale data from the previous session
    # that might still match this suffix (edge case for very fast re-runs)
    _cleanup_by_suffix(suf)
    return suf


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
    return "testPLACEHOLDER_ADMIN_PW"


@pytest.fixture(scope="session")
def isolated_tenant(
    test_tenant_slug: str,
    test_tenant_name: str,
    test_admin_email: str,
    test_admin_password: str,
    auth_headers: dict,
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
        headers=auth_headers,
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
        json={"name": f"test-admin-{test_tenant_slug}", "email": test_admin_email, "role": "admin"},
        headers=auth_headers,
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
        headers=auth_headers,
        timeout=10,
    )
    assert resp.status_code == 200, f"Failed to add tenant member: {resp.text}"

    # Set password for the admin user
    hashed = bcrypt.hashpw(test_admin_password.encode(), bcrypt.gensalt()).decode()
    _stdb_write(f"SELECT set_user_password('{admin_user_id}', '{hashed}')")

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
            headers=auth_headers,
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
