#!/bin/bash
# ──────────────────────────────────────────────────────────────────────
# run-container-tests.sh
#
# Container-based integration test runner for SpacetimeCRM.
# Uses docker-compose.test.yml to spin up a complete test stack:
#   - SpacetimeDB on port 3002 (ephemeral, tmpfs)
#   - FastAPI backend on port 8724
#   - Optional: test runner container for pytest execution
#
# Full lifecycle:
#   Phase 1 — Build test Docker images (STDB module + backend + frontend)
#   Phase 2 — Start test stack via docker-compose
#   Phase 3 — Wait for services to be healthy
#   Phase 4 — Run Python integration tests (pytest)
#   Phase 5 — Run Rust container tests (optional)
#   Cleanup — Stop containers, optionally keep for debugging
#
# Usage:
#   ./scripts/run-container-tests.sh              # full run
#   ./scripts/run-container-tests.sh --no-cleanup  # keep containers for debugging
#   ./scripts/run-container-tests.sh --quick       # skip Docker build, use cached images
#   ./scripts/run-container-tests.sh --with-rust   # also run Rust container tests
#   ./scripts/run-container-tests.sh --help        # show help
# ──────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Config ──────────────────────────────────────────────────────────
COMPOSE_FILE="$REPO_DIR/docker-compose.test.yml"
PROJECT_NAME="spacetime-crm-test"

# Test service ports (non-conflicting with dev)
STDB_HOST="${STDB_HOST:-localhost}"
STDB_PORT="${STDB_PORT:-3002}"
STDB_DB="${STDB_DB:-spacetime-crm-test}"
STDB_URL="http://${STDB_HOST}:${STDB_PORT}"

BACKEND_HOST="${BACKEND_HOST:-localhost}"
BACKEND_PORT="${BACKEND_PORT:-8724}"
BACKEND_URL="http://${BACKEND_HOST}:${BACKEND_PORT}"

CLEANUP=true
BUILD_IMAGES=true
RUN_RUST_TESTS=false

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

START_TIME=$(date +%s)

cleanup_compose() {
  if [ "$CLEANUP" = true ]; then
    log_info "Stopping and removing test containers..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down -v 2>/dev/null || true
    log_pass "Test stack cleaned up$(elapsed)"
  else
    log_info "Containers left running (--no-cleanup). Backend logs:"
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs backend-test --tail 20 2>/dev/null || true
  fi
}

# Trap ensures cleanup on exit
trap 'cleanup_compose' EXIT

# ── Parse args ──────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --no-cleanup) CLEANUP=false ;;
    --quick)      BUILD_IMAGES=false ;;
    --with-rust)  RUN_RUST_TESTS=true ;;
    --help|-h)
      echo "Usage: $0 [--no-cleanup] [--quick] [--with-rust]"
      echo "  --no-cleanup   Keep containers running after tests (for debugging)"
      echo "  --quick        Skip Docker image build, use cached images"
      echo "  --with-rust    Also run Rust container integration tests"
      exit 0
      ;;
    *) echo "Unknown arg: $arg"; exit 1 ;;
  esac
done

echo -e "${CYAN}┌─────────────────────────────────────────┐${NC}"
echo -e "${CYAN}│ SpacetimeCRM Container Integration Tests │${NC}"
echo -e "${CYAN}└─────────────────────────────────────────┘${NC}"
echo "  STDB:  ${STDB_URL}"
echo "  API:   ${BACKEND_URL}"
echo "  Compose: ${COMPOSE_FILE}"

# ════════════════════════════════════════════════════════════════════
# Phase 1 — Build Docker images
# ════════════════════════════════════════════════════════════════════
step "1" "Build Docker test images"

if [ "$BUILD_IMAGES" = true ]; then
  log_info "Building test images (this may take a few minutes on first run)..."
  if docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" build --no-cache 2>&1; then
    log_pass "Test images built$(elapsed)"
  else
    log_fail "Docker build failed"
    exit 1
  fi
else
  log_info "Skipping Docker build (--quick) — using cached images"
fi

# ════════════════════════════════════════════════════════════════════
# Phase 2 — Start test stack
# ════════════════════════════════════════════════════════════════════
step "2" "Start test stack via docker-compose"

log_info "Starting services (spacetime-test, backend-test)..."
if docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d --wait 2>&1; then
  log_pass "Test stack started$(elapsed)"
else
  log_fail "Failed to start test stack"
  docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs --tail 50 2>/dev/null || true
  exit 1
fi

# ════════════════════════════════════════════════════════════════════
# Phase 3 — Verify service health
# ════════════════════════════════════════════════════════════════════
step "3" "Verify service health"

# Check STDB
log_info "Checking STDB at ${STDB_URL}..."
for i in $(seq 1 15); do
  if curl -sf "${STDB_URL}/" >/dev/null 2>&1; then
    log_pass "STDB is healthy$(elapsed)"
    break
  fi
  if [ "$i" -eq 15 ]; then
    log_fail "STDB health check failed"
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs spacetime-test --tail 30
    exit 1
  fi
  sleep 2
done

# Check backend
log_info "Checking backend at ${BACKEND_URL}..."
for i in $(seq 1 30); do
  if curl -sf "${BACKEND_URL}/api/health/ready" >/dev/null 2>&1; then
    log_pass "Backend is healthy$(elapsed)"
    break
  fi
  if [ "$i" -eq 30 ]; then
    log_fail "Backend health check failed"
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs backend-test --tail 50
    exit 1
  fi
  sleep 3
done

# ════════════════════════════════════════════════════════════════════
# Phase 4 — Run Python integration tests
# ════════════════════════════════════════════════════════════════════
step "4" "Run Python integration tests (pytest)"

export CRM_TEST_SERVER="${BACKEND_URL}"
export CRM_ADMIN_EMAIL="${CRM_ADMIN_EMAIL:-admin@crm.local}"
export CRM_ADMIN_PW="${CRM_ADMIN_PW:-PLACEHOLDER_ADMIN_PW}"
export STDB_HOST="${STDB_HOST}"
export STDB_PORT="${STDB_PORT}"
export STDB_DB="${STDB_DB}"

PYTHON_EXIT=0

log_info "Running pytest against containerized backend..."

# Run tests inside the backend-test container for network access
if docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T backend-test \
  sh -c "cd /app/server && python3 -m pytest tests/ -v --tb=short 2>&1"; then
  log_pass "All Python integration tests passed$(elapsed)"
else
  PYTHON_EXIT=$?
  log_fail "Python integration tests failed (exit=${PYTHON_EXIT})"
fi

# ════════════════════════════════════════════════════════════════════
# Phase 5 — Run Rust container tests (optional)
# ════════════════════════════════════════════════════════════════════
RUST_EXIT=0

if [ "$RUN_RUST_TESTS" = true ]; then
  step "5" "Run Rust container integration tests"

  export STDB_CONTAINER_URL="${STDB_URL}"
  export STDB_CONTAINER_DB="${STDB_DB}"

  log_info "Building Rust container test binary..."
  if docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T backend-test \
    sh -c "cargo build --manifest-path /app/server/container-tests/Cargo.toml 2>&1"; then
    log_pass "Rust container test binary built$(elapsed)"
  else
    log_fail "Rust container test build failed"
    RUST_EXIT=1
  fi

  if [ "$RUST_EXIT" -eq 0 ]; then
    log_info "Running container integration tests..."
    if docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec -T backend-test \
      sh -c "/app/server/container-tests/target/debug/container-tests 2>&1"; then
      log_pass "All Rust container integration tests passed$(elapsed)"
    else
      RUST_EXIT=$?
      log_fail "Rust container integration tests failed (exit=${RUST_EXIT})"
    fi
  fi
else
  log_info "Skipping Rust tests (use --with-rust to enable)"
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
  echo -e "${GREEN}│  ALL CONTAINER INTEGRATION TESTS PASSED     │${NC}"
  echo -e "${GREEN}│  Total time: ${TOTAL_TIME}s                        │${NC}"
  echo -e "${GREEN}└────────────────────────────────────────────┘${NC}"
else
  echo -e "${RED}┌────────────────────────────────────────────┐${NC}"
  echo -e "${RED}│  SOME CONTAINER INTEGRATION TESTS FAILED    │${NC}"
  echo -e "${RED}│  Python tests: $([ "$PYTHON_EXIT" -eq 0 ] && echo 'PASS' || echo 'FAIL')                      │${NC}"
  echo -e "${RED}│  Rust tests:   $([ "$RUST_EXIT" -eq 0 ] && echo 'PASS' || echo 'FAIL')                      │${NC}"
  echo -e "${RED}│  Total time: ${TOTAL_TIME}s                        │${NC}"
  echo -e "${RED}└────────────────────────────────────────────┘${NC}"
fi

# ════════════════════════════════════════════════════════════════════
# Cleanup (handled by trap)
# ════════════════════════════════════════════════════════════════════
echo ""
if [ "$CLEANUP" = true ]; then
  log_info "Cleanup will run automatically (trap)$(elapsed)"
else
  log_info "Containers left running (--no-cleanup)$(elapsed)"
  echo "  STDB:  docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} logs spacetime-test"
  echo "  Backend: docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} logs backend-test"
  echo "  Stop: docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} down -v"
fi

exit "$OVERALL_EXIT"