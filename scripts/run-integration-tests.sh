#!/bin/bash
# ──────────────────────────────────────────────────────────────────────
# run-integration-tests.sh
#
# Full-stack integration test suite for SpacetimeCRM.
#
# Full orchestration pipeline:
#   Phase 1 — Build artifacts (STDB WASM module; optionally frontend dist)
#   Phase 2 — Start ephemeral STDB container on port 3002
#   Phase 3 — Publish module to the test instance
#   Phase 4 — Start FastAPI backend against test STDB
#   Phase 5 — Bootstrap test data (admin user + tenant)
#   Phase 6 — Run Python integration tests (pytest) through the backend
#   Phase 7 — Run standalone Rust container tests directly against STDB
#   Cleanup — Stop backend, remove container, report summary
#
# Usage:
#   ./scripts/run-integration-tests.sh               # full run
#   ./scripts/run-integration-tests.sh --no-cleanup   # keep container for debugging
#   ./scripts/run-integration-tests.sh --quick         # skip wasm build, use existing
#   ./scripts/run-integration-tests.sh --with-web      # also build frontend dist
# ──────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Config ──────────────────────────────────────────────────────────
STDB_HOST="${STDB_HOST:-localhost}"
STDB_PORT="${STDB_PORT:-3002}"
STDB_DB="${STDB_DB:-spacetime-crm-test}"
STDB_URL="http://${STDB_HOST}:${STDB_PORT}"
BACKEND_PORT="${BACKEND_PORT:-8723}"
BACKEND_URL="http://${STDB_HOST}:${BACKEND_PORT}"
CONTAINER_NAME="spacetime-crm-test-3002"
IMAGE="spacetimedb/spacetimedb:latest"

CLEANUP=true
BUILD_WASM=true
BUILD_WEB=false
SKIP_CONTAINER=false
BACKEND_PID=""
START_TIME=$(date +%s)

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

cleanup_container() {
  if docker ps -q -f name="$CONTAINER_NAME" 2>/dev/null | grep -q .; then
    log_info "Stopping container ${CONTAINER_NAME}..."
    docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
    log_pass "Container removed"
  fi
}

# Trap ensures backend is always cleaned up on exit
trap 'cleanup_backend; if [ "$CLEANUP" = true ] && [ "$SKIP_CONTAINER" = false ]; then cleanup_container; fi' EXIT

# ── Parse args ──────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --no-cleanup) CLEANUP=false   ;;
    --quick)      BUILD_WASM=false ;;
    --local-stdb) SKIP_CONTAINER=true ;;
    --with-web)   BUILD_WEB=true   ;;
    --help|-h)
      echo "Usage: $0 [--no-cleanup] [--quick] [--with-web]"
      echo "  --no-cleanup   Keep container after run (for debugging)"
      echo "  --quick        Skip WASM build, use existing binary"
      echo "  --with-web     Also build frontend dist (vite build)"
      exit 0
      ;;
    *) echo "Unknown arg: $arg"; exit 1 ;;
  esac
done

echo -e "${CYAN}┌─────────────────────────────────────────┐${NC}"
echo -e "${CYAN}│ SpacetimeCRM Integration Test Runner    │${NC}"
echo -e "${CYAN}└─────────────────────────────────────────┘${NC}"
echo "  DB: ${STDB_DB} @ ${STDB_HOST}:${STDB_PORT}"
echo "  API: ${BACKEND_URL}"

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
    log_fail "Run without --quick once to build it, or rebuild with: make build-stdb"
    exit 1
  fi
  log_info "Skipping WASM build (--quick) — using existing binary"
fi

if [ "$BUILD_WEB" = true ]; then
  log_info "Building frontend dist (vite)..."
  cd "$REPO_DIR/web"
  if npm ci 2>&1 && npm run build 2>&1; then
    log_pass "Frontend dist built$(elapsed)"
  else
    log_fail "Frontend build failed"
    exit 1
  fi
fi

# ════════════════════════════════════════════════════════════════════
# Phase 2 — Start STDB test container (or use existing local STDB)
# ════════════════════════════════════════════════════════════════════
step "2" "STDB instance"

if [ "$SKIP_CONTAINER" = true ]; then
  log_info "Using existing STDB at ${STDB_URL} (--local-stdb)"
  if ! curl -sf "${STDB_URL}/v1/health" >/dev/null 2>&1; then
    log_fail "Cannot reach STDB at ${STDB_URL}"
    exit 1
  fi
  log_pass "STDB reachable at ${STDB_URL}$(elapsed)"
else
  # Pre-check: Docker must be available
  if ! command -v docker &>/dev/null; then
    log_fail "docker not found on PATH — required to start STDB container"
    log_fail "Use --local-stdb to use an existing STDB instance instead"
    exit 1
  fi
  if ! docker info &>/dev/null; then
    log_fail "Docker daemon is not running — start it with: sudo systemctl start docker"
    log_fail "Or use --local-stdb to use an existing STDB instance"
    exit 1
  fi

  # Kill any leftover container from a previous run
  if docker ps -q -f name="$CONTAINER_NAME" 2>/dev/null | grep -q .; then
    log_warn "Container ${CONTAINER_NAME} already exists — removing first"
    docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
  fi

  log_info "Starting ${IMAGE} on port ${STDB_PORT}..."
  docker run -d \
    --name "$CONTAINER_NAME" \
    -p "${STDB_PORT}:3001" \
    --health-cmd "curl -sf http://localhost:3001/" \
    --health-interval 3s \
    --health-timeout 2s \
    --health-retries 20 \
    --health-start-period 8s \
    --tmpfs /var/lib/spacetimedb \
    "$IMAGE" >/dev/null

  log_info "Waiting for STDB to become healthy..."

  RETRIES=30
  for i in $(seq 1 $RETRIES); do
    if curl -sf "$STDB_URL/" >/dev/null 2>&1; then
      log_pass "STDB is ready at ${STDB_URL}$(elapsed)"
      break
    fi
    if [ "$i" -eq "$RETRIES" ]; then
      log_fail "STDB did not become healthy after ${RETRIES} attempts"
      docker logs "$CONTAINER_NAME" 2>&1 | tail -20
      exit 1
    fi
    sleep 2
  done
fi

# ════════════════════════════════════════════════════════════════════
# Phase 3 — Publish module to test instance
# ════════════════════════════════════════════════════════════════════
step "3" "Publish module"

cd "$REPO_DIR/server/spacetimedb"
if spacetime publish \
  --server "$STDB_URL" \
  --yes \
  --delete-data=always \
  "$STDB_DB" 2>&1; then
  log_pass "Module published to '${STDB_DB}'$(elapsed)"
else
  log_fail "Module publish failed"
  if [ "$SKIP_CONTAINER" = false ]; then
    docker logs "$CONTAINER_NAME" 2>&1 | tail -10
  fi
  exit 1
fi

# ════════════════════════════════════════════════════════════════════
# Phase 4 — Start FastAPI backend (before bootstrap so login check works)
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
# Phase 5 — Bootstrap test data (backend is running, login check works)
# ════════════════════════════════════════════════════════════════════
step "5" "Bootstrap test data"

cd "$REPO_DIR"
if STDB_HOST="$STDB_HOST" STDB_PORT="$STDB_PORT" STDB_DB="$STDB_DB" \
  CRM_API_URL="$BACKEND_URL" \
  python3 scripts/bootstrap.py 2>&1; then
  log_pass "Bootstrap data seeded$(elapsed)"
else
  log_fail "bootstrap.py failed — admin user or seed data not created"
  exit 1
fi

# ════════════════════════════════════════════════════════════════════
# Phase 6 — Python backend integration tests (backend from Phase 4)
# ════════════════════════════════════════════════════════════════════
step "6" "Python backend integration tests"

export CRM_TEST_SERVER="${BACKEND_URL}"
export CRM_ADMIN_EMAIL="${CRM_ADMIN_EMAIL:-admin@crm.local}"
export CRM_ADMIN_PW="${CRM_ADMIN_PW:-admin123}"
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
  if [ "$SKIP_CONTAINER" = false ]; then
    cleanup_container
  fi
  log_pass "Cleanup complete$(elapsed)"
else
  log_info "Container left running (--no-cleanup). Backend was already stopped."
  cleanup_backend
fi

exit "$OVERALL_EXIT"
