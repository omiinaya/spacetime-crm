#!/usr/bin/env python3
"""
SpacetimeCRM — Restore Script
Restores STDB tables from a backup JSON.gz file.

Usage:
    python3 scripts/restore.py [--dry-run] [--checksum-algo sha256] backups/spacetime-crm-backup-*.json.gz

Options:
    --dry-run             Validate only — don't delete or restore
    --checksum-algo algo  Compute checksum (default: none). Run: sha256sum <file>

Pre-flight checks:
  - Backup file exists and is not empty
  - Valid JSON (not corrupted)
  - Target database is reachable
  - WASM file exists if not --dry-run
"""

import argparse
import json
import gzip
import hashlib
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


def file_exists_valid(path: Path) -> tuple[bool, str]:
    """Returns (ok, error_message)"""
    if not path.exists():
        return False, f"File not found: {path}"
    if path.stat().st_size == 0:
        return False, f"File is empty: {path}"
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            json.load(f)
    except (json.JSONDecodeError, OSError, EOFError) as e:
        return False, f"Corrupted or invalid backup: {e}"
    return True, ""


def compute_checksum(path: Path) -> str:
    """Compute SHA256 of the raw .gz file."""
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def stdb_reachable() -> tuple[bool, str]:
    """Check if STDB is running and accessible."""
    try:
        client = httpx.Client(timeout=5)
        resp = client.get(f"http://{STDB_HOST}:{STDB_PORT}/")
        if resp.status_code < 500:
            return True, ""
        return False, f"STDB returned status {resp.status_code}"
    except Exception as e:
        return False, f"Cannot reach SpacetimeDB at {STDB_HOST}:{STDB_PORT}: {e}"


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
        print(f"❌ spacetime command failed: {' '.join(cmd)}")
        print(f"   stderr: {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(
        description="Restore STDB tables from a backup JSON.gz file."
    )
    parser.add_argument("file", help="Path to backup .json.gz file")
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate only — don't delete or restore"
    )
    parser.add_argument(
        "--checksum-algo",
        choices=["sha256"],
        default=None,
        help="Compute checksum of the backup file",
    )
    args = parser.parse_args()

    backup_file = Path(args.file)

    # ── Pre-flight validation ──────────────────────────
    print("🔍 Pre-flight validation...")
    ok, err = file_exists_valid(backup_file)
    if not ok:
        print(f"❌ {err}")
        sys.exit(1)
    print(
        f"  ✅ Backup file valid: {backup_file.name} ({backup_file.stat().st_size} bytes)"
    )

    if args.checksum_algo:
        checksum = compute_checksum(backup_file)
        print(f"  📝 Checksum ({args.checksum_algo}): {checksum}")

    ok, err = stdb_reachable()
    if not ok:
        print(f"❌ {err}")
        print("   Ensure 'spacetime start -l 3001' is running")
        sys.exit(1)
    print(f"  ✅ SpacetimeDB reachable at {STDB_HOST}:{STDB_PORT}")

    if not args.dry_run:
        if not WASM_FILE.exists():
            print(f"❌ STDB module wasm not found at: {WASM_FILE}")
            print(
                "   Build it first: cd server/spacetimedb && cargo build --release --target wasm32-unknown-unknown"
            )
            sys.exit(1)
        print(f"  ✅ WASM module exists: {WASM_FILE}")
    else:
        print(f"  ⏩ Skipping WASM check (dry-run)")

    print(f"  ✅ All pre-flight checks passed.")

    if args.dry_run:
        print(f"\n--- Dry-run mode: no changes made ---")
        sys.exit(0)

    # ── Interactive confirmation ───────────────────────
    confirm()

    # Load backup
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
                args = []
                for key, val in row.items():
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
