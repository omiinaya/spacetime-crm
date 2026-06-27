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
WASM_FILE="/app/spacetime_crm.wasm"

if [ -f "$WASM_FILE" ]; then
    echo "📦 Checking if module '$DB_NAME' is published..."
    # The spacetime CLI outputs "No databases found" or a table with columns
    EXISTING=$(spacetime list --server "http://${STDB_HOST:-spacetime}:${STDB_PORT:-3001}" 2>/dev/null | grep -w "$DB_NAME" || true)
    if [ -z "$EXISTING" ]; then
        echo "📦 Publishing STDB module '$DB_NAME'..."
        spacetime publish \
            --server "http://${STDB_HOST:-spacetime}:${STDB_PORT:-3001}" \
            --yes \
            "$DB_NAME" \
            -f "$WASM_FILE"
        echo "✅ Module published"
    else
        echo "✅ Module '$DB_NAME' already published, skipping"
    fi
else
    echo "⚠️  No wasm module found at $WASM_FILE — skipping publish"
    echo "   Build it with: cd server/spacetimedb && cargo build --release --target wasm32-unknown-unknown"
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
