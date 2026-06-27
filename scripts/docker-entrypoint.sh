#!/bin/bash
set -e

# ── Wait for SpacetimeDB ───────────────────────────────────
echo "⏳ Waiting for SpacetimeDB at ${STDB_HOST:-spacetime}:${STDB_PORT:-3001}..."
for i in $(seq 1 60); do
    if curl -sf "http://${STDB_HOST:-spacetime}:${STDB_PORT:-3001}/" > /dev/null 2>&1; then
        echo "✅ SpacetimeDB is ready"
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo "❌ SpacetimeDB failed to start within 60s"
        exit 1
    fi
    sleep 1
done

# ── Publish STDB Module if not already published ───────────
DB_NAME="${STDB_DB:-spacetime-crm}"
MODULE_DIR="/app/server/spacetimedb"

if [ -d "$MODULE_DIR" ]; then
    echo "📦 Checking if module '$DB_NAME' is published..."
    EXISTING=$(spacetime list --server "http://${STDB_HOST:-spacetime}:${STDB_PORT:-3001}" 2>/dev/null | grep -w "$DB_NAME" || true)
    if [ -z "$EXISTING" ]; then
        echo "📦 Publishing STDB module '$DB_NAME'..."
        cd "$MODULE_DIR"
        spacetime publish \
            --server "http://${STDB_HOST:-spacetime}:${STDB_PORT:-3001}" \
            --yes \
            "$DB_NAME"
        echo "✅ Module published"
    else
        echo "✅ Module '$DB_NAME' already published, skipping"
    fi
else
    echo "⚠️  No STDB module source found at $MODULE_DIR — skipping publish"
    echo "   The module directory must be included in the Docker image"
fi

# ── Wait a moment for STDB to settle ───────────────────────
sleep 2

# ── Start Python server ────────────────────────────────────
echo "🚀 Starting backend on port ${SERVER_PORT:-8723}..."
if [ "${RELOAD:-false}" = "true" ]; then
    exec python3 main.py
else
    exec python3 -m uvicorn main:app --host 0.0.0.0 --port "${SERVER_PORT:-8723}"
fi
