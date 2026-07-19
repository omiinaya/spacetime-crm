#!/bin/bash
# ──────────────────────────────────────────────────────────────────────
# verify-test-infra.sh
# Verifies that the container-based integration test infrastructure
# has all required components and they are properly wired together.
#
# Exit codes:
#   0 = all checks pass
#   1 = any check fails
# ──────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
FAILED=0
TOTAL=0

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

pass() { TOTAL=$((TOTAL+1)); echo -e "${GREEN}✓${NC} $1"; }
fail() { TOTAL=$((TOTAL+1)); FAILED=$((FAILED+1)); echo -e "${RED}✗${NC} $1"; }

echo "╔══════════════════════════════════════════════╗"
echo "║  Container Integration Test Infrastructure  ║"
echo "║  Verification                                ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ── 1. docker-compose.test.yml ──────────────────────────────────────
echo "── Phase 1: docker-compose.test.yml ──"

if [ -f "$REPO_DIR/docker-compose.test.yml" ]; then
  pass "docker-compose.test.yml exists"
else
  fail "docker-compose.test.yml missing"
fi

if grep -q "spacetime-test" "$REPO_DIR/docker-compose.test.yml"; then
  pass "docker-compose.test.yml: spacetime-test service defined"
else
  fail "docker-compose.test.yml: spacetime-test service missing"
fi

if grep -q "backend-test" "$REPO_DIR/docker-compose.test.yml"; then
  pass "docker-compose.test.yml: backend-test service defined"
else
  fail "docker-compose.test.yml: backend-test service missing"
fi

if grep -q "test-runner" "$REPO_DIR/docker-compose.test.yml"; then
  pass "docker-compose.test.yml: test-runner service defined"
else
  fail "docker-compose.test.yml: test-runner service missing"
fi

if grep -q "tmpfs" "$REPO_DIR/docker-compose.test.yml"; then
  pass "docker-compose.test.yml: ephemeral storage (tmpfs) configured"
else
  fail "docker-compose.test.yml: tmpfs not configured"
fi

if grep -q "healthcheck" "$REPO_DIR/docker-compose.test.yml"; then
  pass "docker-compose.test.yml: healthchecks configured"
else
  fail "docker-compose.test.yml: healthchecks missing"
fi

# ── 2. server/Dockerfile.test ──────────────────────────────────────
echo ""
echo "── Phase 2: server/Dockerfile.test ──"

if [ -f "$REPO_DIR/server/Dockerfile.test" ]; then
  pass "server/Dockerfile.test exists"
else
  fail "server/Dockerfile.test missing"
fi

# Check that it has all needed deps
if grep -q "playwright" "$REPO_DIR/server/Dockerfile.test"; then
  pass "Dockerfile.test: playwright installed"
else
  fail "Dockerfile.test: playwright missing"
fi

if grep -q "pytest" "$REPO_DIR/server/Dockerfile.test"; then
  pass "Dockerfile.test: pytest installed"
else
  fail "Dockerfile.test: pytest missing"
fi

if grep -q "spacetime" "$REPO_DIR/server/Dockerfile.test"; then
  pass "Dockerfile.test: spacetime CLI installed"
else
  fail "Dockerfile.test: spacetime CLI missing"
fi

# ── 3. scripts/test-entrypoint.sh ───────────────────────────────────
echo ""
echo "── Phase 3: scripts/test-entrypoint.sh ──"

if [ -f "$REPO_DIR/scripts/test-entrypoint.sh" ]; then
  pass "scripts/test-entrypoint.sh exists"
else
  fail "scripts/test-entrypoint.sh missing"
fi

if grep -q "bootstr" "$REPO_DIR/scripts/test-entrypoint.sh"; then
  pass "test-entrypoint.sh: bootstrap logic present"
else
  fail "test-entrypoint.sh: no bootstrap logic"
fi

if grep -q "publish" "$REPO_DIR/scripts/test-entrypoint.sh"; then
  pass "test-entrypoint.sh: publish logic present"
else
  fail "test-entrypoint.sh: no publish logic"
fi

# ── 4. scripts/run-integration-tests.sh ────────────────────────────
echo ""
echo "── Phase 4: scripts/run-integration-tests.sh ──"

if [ -f "$REPO_DIR/scripts/run-integration-tests.sh" ]; then
  pass "scripts/run-integration-tests.sh exists"
else
  fail "scripts/run-integration-tests.sh missing"
fi

if grep -q "Phase 1\|Build artifacts" "$REPO_DIR/scripts/run-integration-tests.sh"; then
  pass "run-integration-tests.sh: build phase present"
else
  fail "run-integration-tests.sh: build phase missing"
fi

if grep -q "Phase 2\|Start" "$REPO_DIR/scripts/run-integration-tests.sh"; then
  pass "run-integration-tests.sh: container start phase present"
else
  fail "run-integration-tests.sh: container start phase missing"
fi

if grep -q "Phase 3\|Publish" "$REPO_DIR/scripts/run-integration-tests.sh"; then
  pass "run-integration-tests.sh: publish phase present"
else
  fail "run-integration-tests.sh: publish phase missing"
fi

if grep -q "Phase 4\|Start FastAPI" "$REPO_DIR/scripts/run-integration-tests.sh"; then
  pass "run-integration-tests.sh: backend start phase present"
else
  fail "run-integration-tests.sh: backend phase missing"
fi

if grep -q "Phase 5\|Bootstr" "$REPO_DIR/scripts/run-integration-tests.sh"; then
  pass "run-integration-tests.sh: bootstrap phase present"
else
  fail "run-integration-tests.sh: bootstrap phase missing"
fi

if grep -q "Phase 6\|Python backend" "$REPO_DIR/scripts/run-integration-tests.sh"; then
  pass "run-integration-tests.sh: Python test phase present"
else
  fail "run-integration-tests.sh: Python test phase missing"
fi

if grep -q "Phase 7\|Rust container" "$REPO_DIR/scripts/run-integration-tests.sh"; then
  pass "run-integration-tests.sh: Rust test phase present"
else
  fail "run-integration-tests.sh: Rust test phase missing"
fi

if grep -q "cleanup\|cleanup_container" "$REPO_DIR/scripts/run-integration-tests.sh"; then
  pass "run-integration-tests.sh: cleanup phase present"
else
  fail "run-integration-tests.sh: cleanup phase missing"
fi

# ── 5. server/container-tests ──────────────────────────────────────
echo ""
echo "── Phase 5: Rust Container Tests ──"

if [ -f "$REPO_DIR/server/container-tests/Cargo.toml" ]; then
  pass "container-tests/Cargo.toml exists"
else
  fail "container-tests/Cargo.toml missing"
fi

if [ -f "$REPO_DIR/server/container-tests/src/main.rs" ]; then
  pass "container-tests/src/main.rs exists"
else
  fail "container-tests/src/main.rs missing"
fi

# Count test functions
TEST_COUNT=$(grep -c "^fn test_" "$REPO_DIR/server/container-tests/src/main.rs" || true)
if [ "$TEST_COUNT" -ge 5 ]; then
  pass "container-tests: $TEST_COUNT test functions defined"
else
  fail "container-tests: only $TEST_COUNT test functions (expected >=5)"
fi

# ── 6. Makefile targets ────────────────────────────────────────────
echo ""
echo "── Phase 6: Makefile Targets ──"

if grep -q "^test-container:" "$REPO_DIR/Makefile"; then
  pass "Makefile: test-container target present"
else
  fail "Makefile: test-container target missing"
fi

if grep -q "^test-rust-container:" "$REPO_DIR/Makefile"; then
  pass "Makefile: test-rust-container target present"
else
  fail "Makefile: test-rust-container target missing"
fi

# ── 7. Python test conftest.py ─────────────────────────────────────
echo ""
echo "── Phase 7: Python Integration Tests ──"

if [ -f "$REPO_DIR/server/tests/conftest.py" ]; then
  pass "server/tests/conftest.py exists"
else
  fail "server/tests/conftest.py missing"
fi

if grep -q "CRM_TEST_SERVER" "$REPO_DIR/server/tests/conftest.py"; then
  pass "conftest.py: uses CRM_TEST_SERVER env var for container-compatible testing"
else
  fail "conftest.py: does not use CRM_TEST_SERVER"
fi

if grep -q "session_suffix" "$REPO_DIR/server/tests/conftest.py"; then
  pass "conftest.py: session isolation via session_suffix"
else
  fail "conftest.py: no session isolation"
fi

if grep -q "_cleanup_by_suffix\|_cleanup_tracked" "$REPO_DIR/server/tests/conftest.py"; then
  pass "conftest.py: cleanup logic present"
else
  fail "conftest.py: no cleanup logic"
fi

# Count Python test files
PYTEST_COUNT=$(find "$REPO_DIR/server/tests" -name "test_*.py" | wc -l)
if [ "$PYTEST_COUNT" -ge 20 ]; then
  pass "server/tests/: $PYTEST_COUNT test files"
else
  fail "server/tests/: only $PYTEST_COUNT test files (expected >=20)"
fi

# ── 8. CI/CD pipeline ──────────────────────────────────────────────
echo ""
echo "── Phase 8: CI/CD Pipeline ──"

if [ -f "$REPO_DIR/.github/workflows/test.yml" ]; then
  pass ".github/workflows/test.yml exists"
else
  fail ".github/workflows/test.yml missing"
fi

if grep -q "spacetimedb" "$REPO_DIR/.github/workflows/test.yml"; then
  pass "CI: SpacetimeDB service container configured"
else
  fail "CI: SpacetimeDB service container not configured"
fi

if grep -q "pytest" "$REPO_DIR/.github/workflows/test.yml"; then
  pass "CI: pytest step configured"
else
  fail "CI: pytest step missing"
fi

if grep -q "publish" "$REPO_DIR/.github/workflows/test.yml"; then
  pass "CI: module publish step configured"
else
  fail "CI: module publish step missing"
fi

# ── Summary ─────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  Summary                                     ║"
echo "╚══════════════════════════════════════════════╝"
echo "  $TOTAL checks, $FAILED failures"
echo ""

exit $FAILED
