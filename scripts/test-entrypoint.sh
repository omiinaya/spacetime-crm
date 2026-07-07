#!/bin/bash
# ──────────────────────────────────────────────────────────────────────
# test-entrypoint.sh
#
# Container entrypoint for SpacetimeCRM backend test service.
#
# Responsibilities:
#   1. Wait for SpacetimeDB to be ready (via service name resolution)
#   2. Publish the STDB module to the test database
#   3. Bootstrap test data (admin user + tenant)
#   4. Start the FastAPI backend server
#
# Environment variables (all optional, with defaults):
#   STDB_HOST       - SpacetimeDB hostname (default: spacetime-test)
#   STDB_PORT       - SpacetimeDB port (default: 3001)
#   STDB_DB         - Database name (default: spacetime-crm-test)
#   SERVER_PORT     - Backend port (default: 8723)
#   JWT_SECRET      - JWT signing secret (required)
#   CRM_ADMIN_EMAIL - Admin email for bootstrap (default: admin@crm.local)
#   CRM_ADMIN_PW    - Admin password for bootstrap (default: admin123)
#   LOG_LEVEL       - Python log level (default: info)
#   RELOAD          - Enable uvicorn reload (default: false)
# ──────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────
STDB_HOST="${STDB_HOST:-spacetime-test}"
STDB_PORT="${STDB_PORT:-3001}"
STDB_DB="${STDB_DB:-spacetime-crm-test}"
SERVER_PORT="${SERVER_PORT:-8723}"
JWT_SECRET="${JWT_SECRET:-test-secret-change-in-production}"
CRM_ADMIN_EMAIL="${CRM_ADMIN_EMAIL:-admin@crm.local}"
CRM_ADMIN_PW="${CRM_ADMIN_PW:-admin123}"
LOG_LEVEL="${LOG_LEVEL:-info}"
RELOAD="${RELOAD:-false}"

STDB_URL="http://${STDB_HOST}:${STDB_PORT}"
MODULE_DIR="/app/server/spacetimedb"

# ── Logging helpers ──────────────────────────────────────────────────
log_info()  { echo -e "\033[0;36m[INFO]\033[0m  $*"; }
log_pass()  { echo -e "\033[0;32m[PASS]\033[0m  $*"; }
log_warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
log_fail()  { echo -e "\033[0;31m[FAIL]\033[0m  $*"; }

# ── Step 1: Wait for SpacetimeDB ─────────────────────────────────────
log_info "Waiting for SpacetimeDB at ${STDB_URL}..."

for i in $(seq 1 60); do
    if curl -sf "${STDB_URL}/v1/health" > /dev/null 2>&1; then
        log_pass "SpacetimeDB is ready at ${STDB_URL}"
        break
    fi
    if [ "$i" -eq 60 ]; then
        log_fail "SpacetimeDB failed to start within 60 seconds"
        exit 1
    fi
    sleep 1
done

# ── Step 2: Publish STDB Module ──────────────────────────────────────
log_info "Checking if module '${STDB_DB}' is published..."

# Use spacetime CLI to check if module exists
if spacetime list --server "${STDB_URL}" 2>/dev/null | grep -qw "${STDB_DB}"; then
    log_pass "Module '${STDB_DB}' already published, skipping"
else
    log_info "Publishing STDB module '${STDB_DB}'..."
    cd "${MODULE_DIR}"
    if spacetime publish \
        --server "${STDB_URL}" \
        --yes \
        --delete-data=always \
        "${STDB_DB}" 2>&1; then
        log_pass "Module published successfully"
    else
        log_fail "Module publish failed"
        exit 1
    fi
fi

# ── Step 3: Wait for module to settle ────────────────────────────────
log_info "Waiting for module to settle..."
sleep 3

# ── Step 4: Bootstrap test data ──────────────────────────────────────
log_info "Bootstrapping test data (admin user + tenant)..."

cd /app/server

# Create bootstrap script inline to avoid extra file
python3 << 'PYEOF'
import os
import sys
import httpx
import bcrypt

STDB_HOST = os.environ.get("STDB_HOST", "spacetime-test")
STDB_PORT = int(os.environ.get("STDB_PORT", "3001"))
STDB_DB = os.environ.get("STDB_DB", "spacetime-crm-test")
SERVER_URL = f"http://localhost:{os.environ.get('SERVER_PORT', '8723')}"
ADMIN_EMAIL = os.environ.get("CRM_ADMIN_EMAIL", "admin@crm.local")
ADMIN_PW = os.environ.get("CRM_ADMIN_PW", "admin123")

sql_url = f"http://{STDB_HOST}:{STDB_PORT}/v1/database/{STDB_DB}/sql"

def run_sql(query: str):
    resp = httpx.post(sql_url, content=query, headers={"Content-Type": "application/sql"}, timeout=10)
    if resp.status_code != 200:
        return None
    return resp.json()

# Check if admin user already exists
result = run_sql(f"SELECT id, email FROM user WHERE email = '{ADMIN_EMAIL}'")
if result and result.get("rows") and len(result["rows"]) > 0:
    print(f"✅ Admin user already exists: {result['rows'][0]}")
    sys.exit(0)

# Create tenant
call_url = f"http://{STDB_HOST}:{STDB_PORT}/v1/database/{STDB_DB}/call"
tenant_resp = httpx.post(
    f"{call_url}/create_tenant",
    json=["Test Tenant", "test-tenant"],
    headers={"Content-Type": "application/json"},
    timeout=10
)
print(f"Tenant create: {tenant_resp.status_code} - {tenant_resp.text[:200]}")

# Create admin user - create_user(tenant_id, email, name, role)
user_resp = httpx.post(
    f"{call_url}/create_user",
    json=["test-tenant", ADMIN_EMAIL, "Admin User", "admin"],
    headers={"Content-Type": "application/json"},
    timeout=10
)
print(f"User create: {user_resp.status_code} - {user_resp.text[:200]}")

# Set password
if user_resp.status_code == 200:
    try:
        user_data = user_resp.json()
        if user_data and "id" in user_data:
            uid = user_data["id"]
            hashed = bcrypt.hashpw(ADMIN_PW.encode(), bcrypt.gensalt()).decode()
            pw_resp = httpx.post(
                f"{call_url}/set_user_password",
                json=[uid, hashed],
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            print(f"Password set: {pw_resp.status_code} - {pw_resp.text[:200]}")
    except Exception as e:
        print(f"Warning: Could not set password: {e}")

# Add admin as tenant member
member_resp = httpx.post(
    f"{call_url}/add_tenant_member",
    json=["test-tenant", "admin", "admin"],
    headers={"Content-Type": "application/json"},
    timeout=10
)
print(f"Member added: {member_resp.status_code} - {member_resp.text[:200]}")

print("✅ Bootstrap complete")
PYEOF

# ── Step 5: Start Backend Server ─────────────────────────────────────
log_info "Starting FastAPI backend on port ${SERVER_PORT}..."

# Export env vars for the Python process
export STDB_HOST="${STDB_HOST}"
export STDB_PORT="${STDB_PORT}"
export STDB_DB="${STDB_DB}"
export SERVER_PORT="${SERVER_PORT}"
export JWT_SECRET="${JWT_SECRET}"
export JWT_EXPIRE_HOURS="${JWT_EXPIRE_HOURS:-24}"
export CRM_ADMIN_EMAIL="${CRM_ADMIN_EMAIL}"
export CRM_ADMIN_PW="${CRM_ADMIN_PW}"
export LOG_LEVEL="${LOG_LEVEL}"

if [ "${RELOAD}" = "true" ]; then
    exec python3 main.py
else
    exec python3 -m uvicorn main:app --host 0.0.0.0 --port "${SERVER_PORT}" --log-level "${LOG_LEVEL}"
fi