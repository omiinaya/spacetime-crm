#!/bin/bash
# ──────────────────────────────────────────────────────────────────────
# run-integration-tests.sh
#
# Full-stack integration test suite for SpacetimeCRM.
#
# What it does (full orchestration):
#   1. Builds the STDB WASM module (or skips with --quick)
#   2. Starts an ephemeral STDB container on port 3002
#   3. Publishes the module to the test instance
#   4. Seeds bootstrap data (admin user + tenant)
#   5. Starts the FastAPI backend connected to the test STDB
#   6. Runs the Python integration test suite (pytest) against the backend
#   7. Runs standalone Rust container tests directly against STDB
#   8. Reports pass/fail and cleans up the container
#
# Usage:
#   ./scripts/run-integration-tests.sh          # full run
#   ./scripts/run-integration-tests.sh --no-cleanup   # keep container for debugging
#   ./scripts/run-integration-tests.sh --quick         # skip wasm build, use existing
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

STDB_HOST="${STDB_HOST:-localhost}"
STDB_PORT="${STDB_PORT:-3002}"
STDB_DB="${STDB_DB:-spacetime-crm-test}"
SERVER_URL="http://${STDB_HOST}:${STDB_PORT}"
COMPOSE_FILE="${REPO_DIR}/docker-compose.test.yml"
CLEANUP=true
BUILD=true
BACKEND_PID=""

# Ensure backend is killed on any exit
cleanup_backend() {
  if [ -n "$BACKEND_PID" ]; then
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup_backend EXIT

# ── Parse args ──────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --no-cleanup) CLEANUP=false ;;
    --quick)      BUILD=false   ;;
    *) echo "Unknown arg: $arg"; exit 1 ;;
  esac
done

# ── Colors ──────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
PASS="${GREEN}✓${NC}"
FAIL="${RED}✗${NC}"
INFO="${CYAN}ℹ${NC}"

echo -e "${CYAN}┌─────────────────────────────────────────┐${NC}"
echo -e "${CYAN}│ SpacetimeCRM Integration Test Runner    │${NC}"
echo -e "${CYAN}└─────────────────────────────────────────┘${NC}"
echo ""

# ── Phase 1: Build WASM module ────────────────────────────────────
if [ "$BUILD" = true ]; then
  echo -e "${INFO} Building STDB WASM module..."
  cd "$REPO_DIR/server/spacetimedb"
  if cargo build --release --target wasm32-unknown-unknown 2>&1; then
    echo -e "${PASS} WASM module built"
  else
    echo -e "${FAIL} WASM build failed"
    exit 1
  fi
else
  echo -e "${INFO} Skipping WASM build (--quick)"
fi

# ── Phase 2: Start test STDB container ─────────────────────────────
echo ""
echo -e "${INFO} Starting test STDB container on port ${STDB_PORT}..."

# Check if a test container is already running
CONTAINER_EXISTS=$(docker ps -q -f name=spacetime-crm-test 2>/dev/null || true)

if [ -n "$CONTAINER_EXISTS" ]; then
  echo -e "${YELLOW}⚠ Test container already running — stopping first${NC}"
  docker stop "$CONTAINER_EXISTS" >/dev/null 2>&1 || true
  docker rm "$CONTAINER_EXISTS" >/dev/null 2>&1 || true
fi

# Start container using docker compose (preferred) or raw docker
if command -v docker-compose &>/dev/null; then
  docker-compose -f "$COMPOSE_FILE" up -d --wait 2>&1
elif docker compose version &>/dev/null 2>&1; then
  docker compose -f "$COMPOSE_FILE" up -d --wait 2>&1
else
  # Fallback: raw docker run
  docker run -d \
    --name spacetime-crm-test \
    -p "${STDB_PORT}:3001" \
    --health-cmd "curl -sf http://localhost:3001/" \
    --health-interval 5s \
    --health-timeout 3s \
    --health-retries 15 \
    --health-start-period 10s \
    --tmpfs /var/lib/spacetimedb \
    spacetimedb/spacetimedb:latest
fi

# Wait for healthy
echo -e "${INFO} Waiting for STDB to become healthy..."
RETRIES=30
for i in $(seq 1 $RETRIES); do
  if curl -sf "$SERVER_URL/" >/dev/null 2>&1; then
    echo -e "${PASS} STDB is ready (${SERVER_URL})"
    break
  fi
  if [ "$i" -eq "$RETRIES" ]; then
    echo -e "${FAIL} STDB did not become healthy after ${RETRIES} attempts"
    docker logs spacetime-crm-test 2>&1 | tail -20
    exit 1
  fi
  sleep 2
done

# ── Phase 3: Publish module ────────────────────────────────────────
echo ""
echo -e "${INFO} Publishing module '${STDB_DB}'..."
cd "$REPO_DIR/server/spacetimedb"
if spacetime publish \
  --server "$SERVER_URL" \
  --yes \
  --delete-data=always \
  "$STDB_DB" 2>&1; then
  echo -e "${PASS} Module published"
else
  echo -e "${FAIL} Module publish failed"
  exit 1
fi

# ── Phase 4: Bootstrap test data ───────────────────────────────────
echo ""
echo -e "${INFO} Bootstrapping test data..."
cd "$REPO_DIR"
STDB_HOST="$STDB_HOST" STDB_PORT="$STDB_PORT" STDB_DB="$STDB_DB" \
  python3 scripts/bootstrap.py 2>&1 || echo -e "${YELLOW}⚠ bootstrap.py not found or failed (non-fatal)${NC}"

# ── Phase 4b: Start FastAPI backend ──────────────────────────────
echo ""
echo -e "${INFO} Starting FastAPI backend against test STDB..."
BACKEND_PORT=8723
BACKEND_URL="http://${STDB_HOST}:${BACKEND_PORT}"

cd "$REPO_DIR/server"
STDB_HOST="$STDB_HOST" STDB_PORT="$STDB_PORT" STDB_DB="$STDB_DB" \
  nohup python3 -m uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT \
  > /tmp/crm-test-backend.log 2>&1 &
BACKEND_PID=$!

echo -e "${INFO} Backend PID=${BACKEND_PID}, waiting for health..."
for i in $(seq 1 20); do
  if curl -sf "${BACKEND_URL}/api/health" >/dev/null 2>&1; then
    echo -e "${PASS} Backend is ready (${BACKEND_URL})"
    break
  fi
  if [ "$i" -eq 20 ]; then
    echo -e "${FAIL} Backend did not become healthy after 20 attempts"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
  fi
  sleep 2
done

# ── Phase 5: Run integration tests ────────────────────────────────
echo ""
echo -e "${CYAN}══════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Running Integration Tests${NC}"
echo -e "${CYAN}══════════════════════════════════════════════${NC}"

# Export test environment variables for Python tests (hit FastAPI)
export CRM_TEST_SERVER="${BACKEND_URL}"
export CRM_ADMIN_EMAIL="${CRM_ADMIN_EMAIL:-admin@crm.local}"
export CRM_ADMIN_PW="${CRM_ADMIN_PW:-admin123}"

TEST_EXIT=0
cd "$REPO_DIR/server"

if [ -d "tests" ]; then
  echo ""
  echo -e "${INFO} Python integration tests..."
  if python3 -m pytest tests/ -v --tb=short 2>&1; then
    echo -e "${PASS} All Python integration tests passed"
  else
    TEST_EXIT=$?
    echo -e "${FAIL} Python integration tests failed (exit=${TEST_EXIT})"
  fi
else
  echo -e "${YELLOW}⚠ No tests/ directory found${NC}"
fi

# ── Phase 4c: Stop FastAPI backend ──────────────────────────────
echo ""
echo -e "${INFO} Stopping FastAPI backend..."
if [ -n "$BACKEND_PID" ]; then
  kill "$BACKEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" 2>/dev/null || true
  echo -e "${PASS} Backend stopped"
fi

# ── Phase 5b: Rust container integration tests ──────────────────
echo ""
echo -e "${INFO} Rust container integration tests..."
cd "$REPO_DIR"

export STDB_CONTAINER_URL="${SERVER_URL}"
export STDB_CONTAINER_DB="${STDB_DB}"

# Build the standalone container-test binary
if ! cargo build --manifest-path server/container-tests/Cargo.toml 2>&1; then
  echo -e "${FAIL} Rust container test build failed"
  RUST_EXIT=1
  if [ "$TEST_EXIT" -eq 0 ]; then TEST_EXIT=$RUST_EXIT; fi
else
  if ./server/container-tests/target/debug/container-tests 2>&1; then
    echo -e "${PASS} All Rust container integration tests passed"
  else
    RUST_EXIT=$?
    echo -e "${FAIL} Rust container integration tests failed (exit=${RUST_EXIT})"
    if [ "$TEST_EXIT" -eq 0 ]; then
      TEST_EXIT=$RUST_EXIT
    fi
  fi
fi

# Unset container test env vars
unset STDB_CONTAINER_URL STDB_CONTAINER_DB

# ── Phase 6: Report ───────────────────────────────────────────────
echo ""
if [ "$TEST_EXIT" -eq 0 ]; then
  echo -e "${GREEN}┌─────────────────────────────────────────┐${NC}"
  echo -e "${GREEN}│  ALL INTEGRATION TESTS PASSED            │${NC}"
  echo -e "${GREEN}└─────────────────────────────────────────┘${NC}"
else
  echo -e "${RED}┌─────────────────────────────────────────┐${NC}"
  echo -e "${RED}│  SOME INTEGRATION TESTS FAILED           │${NC}"
  echo -e "${RED}└─────────────────────────────────────────┘${NC}"
fi

# ── Cleanup ────────────────────────────────────────────────────────
if [ "$CLEANUP" = true ]; then
  echo ""
  echo -e "${INFO} Cleaning up test container..."
  # Stop and remove container
  if command -v docker-compose &>/dev/null; then
    docker-compose -f "$COMPOSE_FILE" down -v 2>&1 || true
  elif docker compose version &>/dev/null 2>&1; then
    docker compose -f "$COMPOSE_FILE" down -v 2>&1 || true
  else
    docker stop spacetime-crm-test >/dev/null 2>&1 || true
    docker rm spacetime-crm-test >/dev/null 2>&1 || true
  fi
  echo -e "${PASS} Container cleaned up"
else
  echo -e "${INFO} Container left running (--no-cleanup)"
fi

exit $TEST_EXIT
