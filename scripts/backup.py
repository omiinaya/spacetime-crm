#!/usr/bin/env python3
"""
SpacetimeCRM — Backup Script
Dumps all STDB tables to a timestamped compressed JSON file.

Usage:
    python3 scripts/backup.py                  # backup to ./backups/
    python3 scripts/backup.py /path/to/dir     # backup to custom dir
    python3 scripts/backup.py .                # backup to current dir

Dependencies: httpx (already in project requirements)
"""

import gzip
import json
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import httpx
except ImportError:
    print("❌ httpx is required. Install with: pip install httpx")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────
STDB_HOST = "localhost"
STDB_PORT = 3001
DB_NAME = "spacetime-crm"
SQL_URL = f"http://{STDB_HOST}:{STDB_PORT}/v1/database/{DB_NAME}/sql"

# All tables in order (use STDB accessor names — these are the SQL table names).
# Verified against server/spacetimedb/src/*.rs accessor annotations (34 tables).
# Parents first so restore.py can insert in FK-safe order.
TABLES = [
    # ── Auth / tenant ─────────────────────────────────────────────
    "tenants",
    "tenant_members",
    "user",
    "user_settings",
    # ── Customers ─────────────────────────────────────────────────
    "customer",
    "customer_geolocations",
    # ── Products / inventory ──────────────────────────────────────
    "products",
    "tax_rates",
    "inventory_adjustment",
    # ── Tickets ───────────────────────────────────────────────────
    "ticket",
    "ticket_note",
    "ticket_timer",
    "checklist_templates",
    "ticket_checklist_items",
    # ── Invoicing ─────────────────────────────────────────────────
    "invoices",
    "invoice_line_items",
    "payment",
    "recurring_invoice_rules",
    "saved_payment_methods",
    # ── Appointments ──────────────────────────────────────────────
    "appointment",
    # ── Estimates ─────────────────────────────────────────────────
    "estimates",
    "estimate_line_items",
    # ── Purchase orders ───────────────────────────────────────────
    "purchase_order",
    "purchase_order_line_item",
    # ── POS ───────────────────────────────────────────────────────
    "counter_sale",
    "counter_sale_line_item",
    # ── Config / metadata ─────────────────────────────────────────
    "custom_field_definitions",
    "custom_field_values",
    "gift_cards",
    "sla_configs",
    "scheduled_reports",
    "webhook_subscriptions",
    "push_subscriptions",
    "audit_log",
]


def sql_query(client: httpx.Client, query: str) -> list[dict] | None:
    """Run a SQL query and return rows as dicts.

    Returns None when the query fails (e.g. the table does not exist in the
    deployed module) so callers can distinguish a missing table from an
    empty one.
    """
    resp = client.post(
        SQL_URL,
        content=query,
        headers={"Content-Type": "application/sql"},
        timeout=30,
    )
    if resp.status_code >= 400:
        print(f"  ⚠️  SQL error ({resp.status_code}): {resp.text[:150]}")
        return None
    data = resp.json()
    result: list[dict] = []
    if isinstance(data, list):
        for table_result in data:
            rows = table_result.get("rows", [])
            schema = table_result.get("schema", {})
            cols = [
                e["name"]["some"] for e in schema.get("elements", []) if "some" in e.get("name", {})
            ]
            for row in rows:
                result.append(dict(zip(cols, row, strict=False)))
    return result


def main():
    backup_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("backups")
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Ensure STDB is reachable
    try:
        client = httpx.Client(timeout=10)
        resp = client.get(f"http://{STDB_HOST}:{STDB_PORT}/")
        assert resp.status_code < 500
        print(f"✅ Connected to SpacetimeDB at {STDB_HOST}:{STDB_PORT}")
    except Exception as e:
        print(f"❌ Cannot reach SpacetimeDB: {e}")
        print(f"   Ensure 'spacetime start -l {STDB_PORT}' is running")
        sys.exit(1)

    # Dump each table
    snapshot: dict = {
        "meta": {
            "db": DB_NAME,
            "timestamp": time.time(),
            "date": datetime.utcnow().isoformat(),
            "tables_count": len(TABLES),
        }
    }

    total_rows = 0
    missing = []
    for table in TABLES:
        rows = sql_query(client, f"SELECT * FROM {table}")
        if rows is None:
            missing.append(table)
        else:
            snapshot[table] = rows
            total_rows += len(rows)
            print(f"  ✓ {table}: {len(rows)} rows")

    if missing:
        print(f"\n⚠️  Tables missing from the deployed module (not backed up): {', '.join(missing)}")
        print("   The running STDB module is older than server/spacetimedb/src/. Publish")
        print("   the current module, then re-run this backup to include them.")

    snapshot["meta"]["total_rows"] = total_rows
    snapshot["meta"]["missing_tables"] = missing

    # Write compressed JSON
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"spacetime-crm-backup-{timestamp}.json.gz"
    filepath = backup_dir / filename

    with gzip.open(filepath, "wt", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    mb = filepath.stat().st_size / 1024 / 1024
    print(f"\n✅ Backup saved: {filepath} ({total_rows} rows, {mb:.1f} MB)")
    print(f"   Tables: {len(TABLES)}")


if __name__ == "__main__":
    main()
