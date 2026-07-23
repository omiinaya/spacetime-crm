"""STDB SQL helpers and entity tracking for test isolation."""

from __future__ import annotations

import os
import uuid
import httpx

SERVER_URL = os.environ.get("CRM_TEST_SERVER", "http://localhost:8723")
ADMIN_EMAIL = os.environ.get("CRM_ADMIN_EMAIL", "admin@crm.local")
ADMIN_PW = os.environ.get("CRM_ADMIN_PW", "admin123")

# Test STDB container settings (used by test helpers for direct SQL lookups)
STDB_HOST = os.environ.get("STDB_HOST", "localhost")
STDB_PORT = int(os.environ.get("STDB_TEST_PORT", os.environ.get("STDB_PORT", "3001")))
STDB_DB = os.environ.get("STDB_DB", "spacetime-crm")
STDB_SQL_URL = f"http://{STDB_HOST}:{STDB_PORT}/v1/database/{STDB_DB}/sql"
STDB_CALL_URL = f"http://{STDB_HOST}:{STDB_PORT}/v1/database/{STDB_DB}/call"


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
    "invoice": "invoices",
    "payment": "payment",
    "product": "products",
    "appointment": "appointment",
    "estimate": "estimates",
    "purchase_order": "purchase_order",
    "tax_rate": "tax_rates",
    "user": "user",
    "webhook_subscription": "webhook_subscriptions",
    "recurring_invoice_rule": "recurring_invoice_rules",
    "report_schedule": "scheduled_reports",
    "checklist_template": "checklist_templates",
    "custom_field_definition": "custom_field_definitions",
    "counter_sale": "counter_sale",
    "adjustment": "inventory_adjustment",
    "pos_line_item": "pos_line_item",
    "saved_payment_method": "saved_payment_methods",
    "tenant": "tenants",
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
        # Child/dependent tables (must delete before parents)
        "ticket_checklist_items",
        "ticket_note",
        "ticket_timer",
        "saved_payment_methods",
        "tenant_members",
        "tenants",
        "counter_sale_line_item",
        "pos_line_item",
        "invoice_line_items",
        "estimate_line_items",
        "payment",
        "purchase_order_line_item",
        "inventory_adjustment",
        "appointment",
        "recurring_invoice_rules",
        "webhook_subscriptions",
        "scheduled_reports",
        "custom_field_values",
        "custom_field_definitions",
        "checklist_templates",
        "customer_geolocations",
        # Main entities
        "ticket",
        "invoices",
        "estimates",
        "purchase_order",
        "counter_sale",
        "products",
        "customer",
        "tax_rates",
        "user",
        "user_settings",
        # Audit/config tables
        "audit_log",
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
                f"OR (customer_name IS NOT NULL AND customer_name LIKE '%{suffix}%') "
                f"OR (slug IS NOT NULL AND slug LIKE '%{suffix}%') "
                f"OR (label IS NOT NULL AND label LIKE '%{suffix}%') "
                f"OR (url IS NOT NULL AND url LIKE '%{suffix}%') "
                f"OR (username IS NOT NULL AND username LIKE '%{suffix}%')"
            )
            count += 1
        except Exception:
            pass
    return count
