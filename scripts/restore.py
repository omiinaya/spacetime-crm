#!/usr/bin/env python3
"""
SpacetimeCRM — Restore Script
Restores STDB tables from a backup JSON.gz file.

⚠️ WARNING: This will DELETE the existing database and re-publish the module!
All current data will be lost.

Usage:
    python3 scripts/restore.py backups/spacetime-crm-backup-*.json.gz

Dependencies: httpx (already in project requirements), spacetime CLI
"""

import gzip
import json
import subprocess
import sys
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
STDB_SERVER = f"http://{STDB_HOST}:{STDB_PORT}"
CALL_URL = f"{STDB_SERVER}/v1/database/{DB_NAME}/call"
MODULE_DIR = Path(__file__).resolve().parent.parent / "server" / "spacetimedb"
WASM_FILE = MODULE_DIR / "target" / "wasm32-unknown-unknown" / "release" / "spacetime_crm.wasm"


def confirm():
    ans = input(
        f"\n⚠️  This will DELETE the '{DB_NAME}' database and restore from backup.\n"
        f"   All current data will be lost.\n\n"
        f"   Type 'yes' to continue: "
    )
    if ans.lower() != "yes":
        print("❌ Aborted.")
        sys.exit(1)


def run_spacetime(args: list[str]) -> str:
    """Run a spacetime CLI command and return stdout."""
    cmd = ["spacetime", "--server", STDB_SERVER, *args]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        print(f"  ⚠️  spacetime {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/restore.py <backup_file.json.gz>")
        sys.exit(1)

    backup_file = Path(sys.argv[1])
    if not backup_file.exists():
        print(f"❌ Backup file not found: {backup_file}")
        sys.exit(1)

    # Check spacetime CLI
    try:
        subprocess.run(["spacetime", "--version"], capture_output=True, timeout=10)
    except FileNotFoundError:
        print("❌ spacetime CLI not found. Install it from GitHub releases.")
        print("   https://github.com/clockworklabs/SpacetimeDB/releases")
        sys.exit(1)

    confirm()

    # Load backup
    print(f"📂 Loading backup: {backup_file}")
    with gzip.open(backup_file, "rt", encoding="utf-8") as f:
        backup: dict = json.load(f)

    meta = backup.get("meta", {})
    print(f"   Database: {meta.get('db')}")
    print(f"   Date: {meta.get('date')}")
    print(f"   Total rows: {meta.get('total_rows', '?')}")

    # Step 1: Delete existing database
    print(f"\n🗑️  Deleting database '{DB_NAME}'...")
    run_spacetime(["delete", "-y", DB_NAME])
    print("   ✅ Database deleted")

    # Step 2: Re-publish module
    if not WASM_FILE.exists():
        print(f"\n❌ STDB module wasm not found at: {WASM_FILE}")
        print(
            "   Build it first: cd server/spacetimedb && cargo build --release --target wasm32-unknown-unknown"
        )
        sys.exit(1)

    print(f"\n📦 Publishing STDB module '{DB_NAME}'...")
    result = subprocess.run(
        [
            "spacetime",
            "publish",
            "--server",
            STDB_SERVER,
            "-y",
            DB_NAME,
            "-f",
            str(WASM_FILE),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        print(f"❌ Publish failed: {result.stderr.strip()}")
        sys.exit(1)
    print("   ✅ Module published")

    # Step 3: Restore tables (in order — parent first)
    # Table names MUST match backup keys (STDB accessor names) — e.g. the
    # accessor is `products`, `tax_rates`, `invoices`, `estimates` (plural).
    #
    # Only tables with a dedicated import_* reducer can be restored
    # programmatically: anonymous SQL DML is denied by STDB, so plain INSERT
    # is not an option. Every other table is listed below as skipped with the
    # correct accessor name so the operator knows exactly what needs manual
    # restoration.
    restore_order = [
        # (backup_key, import_reducer, arg_map)
        # arg_map: ordered list of (backup_field, reducer_type) — the reducer
        # takes positional args in a FIXED order that does NOT match dict
        # iteration order, so we map explicitly.
        (
            "customer",
            "import_customer",
            [
                ("tenant_id", "str"),
                ("id", "str"),
                ("first_name", "str"),
                ("last_name", "str"),
                ("email", "str"),
                ("phone", "str"),
                ("mobile", "str"),
                ("address_line_1", "str"),
                ("address_line_2", "str"),
                ("city", "str"),
                ("state", "str"),
                ("zip", "str"),
                ("company", "str"),
                ("notes", "str"),
                ("tags", "str"),
                ("created_at", "int"),
                ("updated_at", "int"),
            ],
        ),
        (
            "products",
            "import_product",
            [
                ("tenant_id", "str"),
                ("id", "str"),
                ("name", "str"),
                ("sku", "str"),
                ("barcode", "str"),
                ("description", "str"),
                ("category", "str"),
                ("price", "float"),
                ("cost", "float"),
                ("quantity_on_hand", "float"),
                ("quantity_committed", "float"),
                ("min_stock", "float"),
                ("reorder_quantity", "float"),
                ("location", "str"),
                ("active", "bool"),
                ("created_at", "int"),
                ("updated_at", "int"),
            ],
        ),
        # Tables without import reducers — listed so the operator sees the
        # full inventory of what needs manual attention after a restore.
        ("tenants", None, None),
        ("tenant_members", None, None),
        ("user", None, None),
        ("user_settings", None, None),
        ("customer_geolocations", None, None),
        ("tax_rates", None, None),
        ("inventory_adjustment", None, None),
        ("ticket", None, None),
        ("ticket_note", None, None),
        ("ticket_timer", None, None),
        ("checklist_templates", None, None),
        ("ticket_checklist_items", None, None),
        ("invoices", None, None),
        ("invoice_line_items", None, None),
        ("payment", None, None),
        ("recurring_invoice_rules", None, None),
        ("saved_payment_methods", None, None),
        ("appointment", None, None),
        ("estimates", None, None),
        ("estimate_line_items", None, None),
        ("purchase_order", None, None),
        ("purchase_order_line_item", None, None),
        ("counter_sale", None, None),
        ("counter_sale_line_item", None, None),
        ("custom_field_definitions", None, None),
        ("custom_field_values", None, None),
        ("gift_cards", None, None),
        ("sla_configs", None, None),
        ("scheduled_reports", None, None),
        ("webhook_subscriptions", None, None),
        ("push_subscriptions", None, None),
        ("audit_log", None, None),
    ]

    print("\n🔄 Restoring tables...")
    client = httpx.Client(timeout=30)
    restored = 0
    skipped = 0

    def coerce(value, type_name: str):
        """Coerce a backup value to the reducer parameter's expected type."""
        if value is None or value == "":
            if type_name == "int":
                return 0
            if type_name == "float":
                return 0.0
            if type_name == "bool":
                return False
            return ""
        if type_name == "int":
            return int(float(value))
        if type_name == "float":
            return float(value)
        if type_name == "bool":
            if isinstance(value, bool):
                return value
            return str(value).lower() in ("1", "true", "yes", "y")
        return str(value)

    for table_name, import_reducer, arg_map in restore_order:
        rows = backup.get(table_name, [])
        if not rows:
            print(f"  - {table_name}: 0 rows (empty)")
            continue

        table_ok = True
        for i, row in enumerate(rows):
            if import_reducer and arg_map:
                # Use the import reducer (ID-preserving) with EXPLICIT arg
                # order — dict iteration order is NOT the reducer's order.
                try:
                    args = [coerce(row.get(key), t) for key, t in arg_map]
                    resp = client.post(
                        f"{CALL_URL}/{import_reducer}",
                        json=args,
                        timeout=30,
                    )
                    if resp.status_code >= 400:
                        print(f"  ⚠️  {table_name}[{i}]: {resp.text[:100]}")
                        table_ok = False
                except Exception as e:
                    print(f"  ⚠️  {table_name}[{i}]: {e}")
                    table_ok = False
                else:
                    restored += 1
            else:
                skipped += 1

        status = "✅" if table_ok else "⚠️"
        print(
            f"  {status} {table_name}: {len(rows)} rows restored"
            + (f" ({import_reducer})" if import_reducer else " [no import reducer — skipped]")
        )

    if skipped:
        print(f"\n⚠️  {skipped} rows skipped (tables without import reducers).")
        print("   These tables need import reducers added to the STDB module.")
        print("   Tables with import reducers: customer, products")
    print(f"\n✅ Restore complete: {restored} rows restored")
    print("   ⚠️  Restore any passwords, settings, or portal hashes manually")


if __name__ == "__main__":
    main()
