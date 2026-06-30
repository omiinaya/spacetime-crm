#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

echo "=== Re-seeding SpacetimeCRM ==="

# Bootstrap (create admin user, tenant, set password)
echo "[1/3] Bootstrapping admin user..."
python3 scripts/bootstrap.py

# Seed demo data
echo "[2/3] Seeding demo data..."
python3 scripts/seed-demo.py

echo "[3/3] Verifying..."
TOKEN=$(curl -s localhost:8723/api/auth/login -H 'Content-Type: application/json' -d '{"email":"admin@crm.local","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))")
echo "Login OK: ${TOKEN:0:20}..."

for table in customers products tickets invoices payments appointments; do
  count=$(curl -s "localhost:8723/api/$table" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; d=json.load(sys.stdin); ks=list(d.keys()); print(len(d.get(ks[0],[])))" 2>/dev/null || echo "?")
  echo "  $table: $count"
done

echo "✅ Re-seed complete"
