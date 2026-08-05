#!/bin/bash
# ──────────────────────────────────────────────────────────────────────
# run-integration-tests-standalone.sh
#
# Like run-integration-tests.sh but uses spacetimedb-standalone binary
# instead of Docker, which isn't available on this system.
#
# Usage: same as original: --quick, --no-cleanup
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Config ──────────────────────────────────────────────────────────
STDB_HOST="${STDB_HOST:-localhost}"
STDB_PORT="${STDB_PORT:-3003}"
STDB_DB="${STDB_DB:-spacetime-crm-test}"
STDB_URL="http://${STDB_HOST}:${STDB_PORT}"
BACKEND_PORT="${BACKEND_PORT:-8724}"
BACKEND_URL="http://${STDB_HOST}:${BACKEND_PORT}"
CONTAINER_NAME="spacetime-crm-test-3003"

CLEANUP=true
BUILD_WASM=true
BACKEND_PID=""
STDB_PID=""
START_TIME=$(date +%s)

STDB_BINARY="/home/hindsight/.local/share/spacetime/bin/2.6.1/spacetimedb-standalone"
SPACETIME_CLI="/home/hindsight/.cargo/bin/spacetime"

# ── Helpers ─────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'
PASS="${GREEN}✓${NC}"
FAIL="${RED}✗${NC}"
INFO="${CYAN}ℹ${NC}"

log_info()  { echo -e "${INFO} $1"; }
log_pass()  { echo -e "${PASS} $1"; }
log_fail()  { echo -e "${FAIL} $1"; }
log_warn()  { echo -e "${YELLOW}⚠ $1${NC}"; }
step()      { echo ""; echo -e "${CYAN}── Phase $1 ──${NC} $2"; }
elapsed()   { local now=$(date +%s); echo " ($((now - START_TIME))s)"; }

cleanup_backend() {
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
    BACKEND_PID=""
  fi
}

cleanup_stdb() {
  if [ -n "$STDB_PID" ]; then
    kill "$STDB_PID" 2>/dev/null || true
    wait "$STDB_PID" 2>/dev/null || true
    STDB_PID=""
  fi
}

# Trap ensures cleanup
trap 'cleanup_backend; if [ "$CLEANUP" = true ]; then cleanup_stdb; fi' EXIT

# ── Parse args ──────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --no-cleanup) CLEANUP=false   ;;
    --quick)      BUILD_WASM=false ;;
    --help|-h)
      echo "Usage: $0 [--no-cleanup] [--quick]"
      exit 0
      ;;
    *) echo "Unknown arg: $arg"; exit 1 ;;
  esac
done

echo -e "${CYAN}┌─────────────────────────────────────────┐${NC}"
echo -e "${CYAN}│ SpacetimeCRM Integration Test Runner    │${NC}"
echo -e "${CYAN}│ (standalone mode — no Docker)           │${NC}"
echo -e "${CYAN}└─────────────────────────────────────────┘${NC}"
echo "  DB: ${STDB_DB} @ ${STDB_HOST}:${STDB_PORT}"
echo "  API: ${BACKEND_URL}"

# ════════════════════════════════════════════════════════════════════
# Phase 0 — Verify tools
# ════════════════════════════════════════════════════════════════════
step "0" "Verify tools"

if [ ! -f "$STDB_BINARY" ]; then
  log_fail "STDB standalone binary not found at $STDB_BINARY"
  exit 1
fi
log_pass "STDB binary found"

if [ ! -f "$SPACETIME_CLI" ]; then
  log_fail "spacetime CLI not found at $SPACETIME_CLI"
  exit 1
fi
log_pass "spacetime CLI found"

# ════════════════════════════════════════════════════════════════════
# Phase 1 — Build artifacts
# ════════════════════════════════════════════════════════════════════
step "1" "Build artifacts"

if [ "$BUILD_WASM" = true ]; then
  log_info "Building STDB WASM module..."
  cd "$REPO_DIR/server/spacetimedb"
  if cargo build --release --target wasm32-unknown-unknown 2>&1; then
    log_pass "WASM module built$(elapsed)"
  else
    log_fail "WASM build failed"
    exit 1
  fi
else
  WASM_BINARY="$REPO_DIR/server/spacetimedb/target/wasm32-unknown-unknown/release/spacetime_crm.wasm"
  if [ ! -f "$WASM_BINARY" ]; then
    log_fail "--quick specified but WASM binary not found at ${WASM_BINARY}"
    exit 1
  fi
  log_info "Skipping WASM build (--quick) — using existing binary"
fi

# ════════════════════════════════════════════════════════════════════
# Phase 2 — Start STDB standalone instance
# ════════════════════════════════════════════════════════════════════
step "2" "Start STDB standalone on port ${STDB_PORT}"

JWT_PRIV_KEY="/home/hindsight/.config/spacetime/id_ecdsa"
JWT_PUB_KEY="/home/hindsight/.config/spacetime/id_ecdsa.pub"

if [ ! -f "$JWT_PRIV_KEY" ]; then
  log_warn "No JWT key found — starting without auth"
  $STDB_BINARY start -l "$STDB_PORT" --data-dir "/tmp/spacetimedb-test-${STDB_PORT}" --in-memory &
  STDB_PID=$!
else
  $STDB_BINARY start \
    --listen-addr "0.0.0.0:${STDB_PORT}" \
    --data-dir "/tmp/spacetimedb-test-${STDB_PORT}" \
    --jwt-priv-key-path "$JWT_PRIV_KEY" \
    --jwt-pub-key-path "$JWT_PUB_KEY" \
    --in-memory &
  STDB_PID=$!
fi

log_info "STDB PID=${STDB_PID}, waiting for readiness..."

RETRIES=30
for i in $(seq 1 $RETRIES); do
  if curl -sf "${STDB_URL}/v1/health" >/dev/null 2>&1; then
    log_pass "STDB is ready at ${STDB_URL}$(elapsed)"
    break
  fi
  if [ "$i" -eq "$RETRIES" ]; then
    log_fail "STDB did not become healthy after ${RETRIES} attempts"
    exit 1
  fi
  sleep 2
done

# ════════════════════════════════════════════════════════════════════
# Phase 3 — Publish module to test instance
# ════════════════════════════════════════════════════════════════════
step "3" "Publish module"

cd "$REPO_DIR/server/spacetimedb"
# Try with auth first; if that fails, try without
if ! $SPACETIME_CLI publish \
  --server "$STDB_URL" \
  --yes \
  --delete-data=always \
  "$STDB_DB" 2>&1; then
  
  log_warn "Auth-required publish failed, trying without server flag..."
  
  # standalone instances started WITHOUT JWT keys don't need auth
  # Let's try with the identity/token
  if ! $SPACETIME_CLI publish \
    --server "$STDB_URL" \
    --yes \
    --delete-data=always \
    "$STDB_DB" 2>&1; then
    log_fail "Module publish failed"
    exit 1
  fi
fi

log_pass "Module published to '${STDB_DB}'$(elapsed)"

# ════════════════════════════════════════════════════════════════════
# Phase 4 — Start FastAPI backend
# ════════════════════════════════════════════════════════════════════
step "4" "Start FastAPI backend"

cd "$REPO_DIR/server"
STDB_HOST="$STDB_HOST" STDB_PORT="$STDB_PORT" STDB_DB="$STDB_DB" \
  nohup python3 -m uvicorn main:app --host 0.0.0.0 --port "$BACKEND_PORT" \
  > /tmp/crm-test-backend.log 2>&1 &
BACKEND_PID=$!

log_info "Backend PID=${BACKEND_PID}, waiting for health..."

for i in $(seq 1 25); do
  if curl -sf "${BACKEND_URL}/api/health" >/dev/null 2>&1; then
    log_pass "Backend ready at ${BACKEND_URL}$(elapsed)"
    break
  fi
  if [ "$i" -eq 25 ]; then
    log_fail "Backend did not become healthy after 25 attempts"
    tail -30 /tmp/crm-test-backend.log 2>/dev/null || true
    exit 1
  fi
  sleep 2
done

# ════════════════════════════════════════════════════════════════════
# Phase 5 — Bootstrap test data
# ════════════════════════════════════════════════════════════════════
step "5" "Bootstrap test data"

cd "$REPO_DIR"
if STDB_HOST="$STDB_HOST" STDB_PORT="$STDB_PORT" STDB_DB="$STDB_DB" \
  CRM_API_URL="$BACKEND_URL" \
  python3 scripts/bootstrap.py 2>&1; then
  log_pass "Bootstrap data seeded$(elapsed)"
else
  log_fail "bootstrap.py failed"
  exit 1
fi

# ════════════════════════════════════════════════════════════════════
# Phase 6 — Python backend integration tests
# ════════════════════════════════════════════════════════════════════
step "6" "Python backend integration tests"

export CRM_TEST_SERVER="${BACKEND_URL}"
export CRM_ADMIN_EMAIL="${CRM_ADMIN_EMAIL:-admin@crm.local}"
export CRM_ADMIN_PW="${CRM_ADMIN_PW:-change-me-in-production}"
export STDB_HOST="${STDB_HOST}"
export STDB_PORT="${STDB_PORT}"
export STDB_DB="${STDB_DB}"

PYTHON_EXIT=0
cd "$REPO_DIR/server"

if [ -d "tests" ]; then
  log_info "Running pytest (tests/)..."
  if python3 -m pytest tests/ -v --tb=short 2>&1; then
    log_pass "All Python integration tests passed$(elapsed)"
  else
    PYTHON_EXIT=$?
    log_fail "Python integration tests failed (exit=${PYTHON_EXIT})"
  fi
else
  log_warn "No tests/ directory found — skipping Python tests"
fi

# ════════════════════════════════════════════════════════════════════
# Phase 7 — Rust container integration tests
# ════════════════════════════════════════════════════════════════════
step "7" "Rust container integration tests"

export STDB_CONTAINER_URL="${STDB_URL}"
export STDB_CONTAINER_DB="${STDB_DB}"

RUST_EXIT=0
cd "$REPO_DIR"

if [ -f "server/container-tests/Cargo.toml" ]; then
  log_info "Building Rust container test binary..."
  if ! cargo build --manifest-path server/container-tests/Cargo.toml 2>&1; then
    log_fail "Rust container test build failed"
    RUST_EXIT=1
  else
    log_info "Running container integration tests..."
    if ./server/container-tests/target/debug/container-tests 2>&1; then
      log_pass "All Rust container integration tests passed$(elapsed)"
    else
      RUST_EXIT=$?
      log_fail "Rust container integration tests failed (exit=${RUST_EXIT})"
    fi
  fi
else
  log_warn "No server/container-tests/ found — skipping Rust tests"
fi

unset STDB_CONTAINER_URL STDB_CONTAINER_DB

# ── Determine overall result ────────────────────────────────────────
if [ "$PYTHON_EXIT" -ne 0 ] || [ "$RUST_EXIT" -ne 0 ]; then
  OVERALL_EXIT=1
else
  OVERALL_EXIT=0
fi

TOTAL_TIME=$(($(date +%s) - START_TIME))

# ════════════════════════════════════════════════════════════════════
# Report
# ════════════════════════════════════════════════════════════════════
echo ""
if [ "$OVERALL_EXIT" -eq 0 ]; then
  echo -e "${GREEN}┌────────────────────────────────────────────┐${NC}"
  echo -e "${GREEN}│  ALL INTEGRATION TESTS PASSED              │${NC}"
  echo -e "${GREEN}│  Total time: ${TOTAL_TIME}s                     │${NC}"
  echo -e "${GREEN}└────────────────────────────────────────────┘${NC}"
else
  echo -e "${RED}┌────────────────────────────────────────────┐${NC}"
  echo -e "${RED}│  SOME INTEGRATION TESTS FAILED             │${NC}"
  echo -e "${RED}│  Python tests: $([ "$PYTHON_EXIT" -eq 0 ] && echo 'PASS' || echo 'FAIL')                    │${NC}"
  echo -e "${RED}│  Rust tests:   $([ "$RUST_EXIT" -eq 0 ] && echo 'PASS' || echo 'FAIL')                    │${NC}"
  echo -e "${RED}│  Total time: ${TOTAL_TIME}s                     │${NC}"
  echo -e "${RED}└────────────────────────────────────────────┘${NC}"
fi

# ════════════════════════════════════════════════════════════════════
# Cleanup
# ════════════════════════════════════════════════════════════════════
echo ""
if [ "$CLEANUP" = true ]; then
  log_info "Cleaning up..."
  cleanup_backend
  cleanup_stdb
  log_pass "Cleanup complete$(elapsed)"
else
  log_info "Leaving running (--no-cleanup)."
  cleanup_backend
fi

exit "$OVERALL_EXIT"
