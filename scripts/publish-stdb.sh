#!/bin/bash
# Manual STDB module build + publish script
# Usage: ./scripts/publish-stdb.sh [database_name]
set -e

cd "$(dirname "$0")/.."

DB_NAME="${1:-spacetime-crm}"
SERVER="http://${STDB_HOST:-localhost}:${STDB_PORT:-3001}"

echo "📦 Building STDB module..."
cd server/spacetimedb
cargo build --release --target wasm32-unknown-unknown
WASM_FILE="target/wasm32-unknown-unknown/release/spacetime_crm.wasm"

if [ ! -f "$WASM_FILE" ]; then
    echo "❌ Build failed — wasm file not found at $WASM_FILE"
    exit 1
fi

echo "📦 Publishing '$DB_NAME' to $SERVER..."
cd server/spacetimedb
spacetime publish \
    --server "$SERVER" \
    --yes \
    "$DB_NAME"

echo "✅ Published '$DB_NAME'"
