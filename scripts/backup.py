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

import json
import gzip
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

# All tables in order (use STDB accessor names — these are the SQL table names)
TABLES = [
    "customer",
    "user",
    "user_settings",
    "products",  # accessor = products
    "tax_rates",  # accessor = tax_rates
    "ticket",
    "ticket_note",
    "ticket_timer",
    "invoices",  # accessor = invoices
    "invoice_line_items",  # accessor = invoice_line_items
    "payment",
    "appointment",
    "estimates",  # accessor = estimates
    "estimate_line_items",  # accessor = estimate_line_items
    "purchase_order",
    "purchase_order_line_item",
    "inventory_adjustment",
    "audit_log",
]


def sql_query(client: httpx.Client, query: str) -> list[dict]:
    """Run a SQL query and return rows as dicts."""
    resp = client.post(
        SQL_URL,
        content=query,
        headers={"Content-Type": "application/sql"},
        timeout=30,
    )
    if resp.status_code >= 400:
        print(f"  ⚠️  SQL error ({resp.status_code}): {resp.text[:150]}")
        return []
    data = resp.json()
    result: list[dict] = []
    if isinstance(data, list):
        for table_result in data:
            rows = table_result.get("rows", [])
            schema = table_result.get("schema", {})
            cols = [
                e["name"]["some"]
                for e in schema.get("elements", [])
                if "some" in e.get("name", {})
            ]
            for row in rows:
                result.append(dict(zip(cols, row)))
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
    for table in TABLES:
        rows = sql_query(client, f"SELECT * FROM {table}")
        snapshot[table] = rows
        total_rows += len(rows)
        status = "✓" if rows is not None else "✗"
        print(f"  {status} {table}: {len(rows)} rows")

    snapshot["meta"]["total_rows"] = total_rows

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
