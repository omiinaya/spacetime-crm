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

import json
import gzip
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
WASM_FILE = (
    MODULE_DIR / "target" / "wasm32-unknown-unknown" / "release" / "spacetime_crm.wasm"
)


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
    restore_order = [
        ("customer", "import_customer"),
        ("user", None),  # no import reducer; needs manual add
        ("product", "import_product"),
        ("tax_rate", None),
        ("ticket", None),
        ("invoice", None),
        ("estimate", None),
        ("payment", None),
        ("appointment", None),
        ("purchase_order", None),
        ("inventory_adjustment", None),
        ("audit_log", None),
    ]

    print(f"\n🔄 Restoring tables...")
    client = httpx.Client(timeout=30)
    restored = 0
    skipped = 0

    for table_name, import_reducer in restore_order:
        rows = backup.get(table_name, [])
        if not rows:
            print(f"  - {table_name}: 0 rows (empty)")
            continue

        table_ok = True
        for i, row in enumerate(rows):
            if import_reducer:
                # Use the import reducer (ID-preserving)
                args = []
                for key, val in row.items():
                    # Coerce to match reducer parameter types
                    if isinstance(val, bool):
                        args.append(val)
                    elif isinstance(val, (int, float)):
                        args.append(val)
                    else:
                        args.append(str(val or ""))
                try:
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
            + (
                f" ({import_reducer})"
                if import_reducer
                else " [no import reducer — skipped]"
            )
        )

    if skipped:
        print(f"\n⚠️  {skipped} rows skipped (tables without import reducers).")
        print("   These tables need import reducers added to the STDB module.")
        print("   Tables with import reducers: customer, product")
    print(f"\n✅ Restore complete: {restored} rows restored")
    print(f"   ⚠️  Restore any passwords, settings, or portal hashes manually")


if __name__ == "__main__":
    main()
