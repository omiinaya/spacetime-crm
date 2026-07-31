# SpacetimeCRM — Test Suite Summary
# Updated: 2026-07-05

| Layer | Tests | Tool | Status |
|-------|-------|------|--------|
| Python backend | 39 | pytest | ✅ Integration |
| Python sanitization | 13 | pytest | ✅ Unit (offline-safe) |
| Rust type-check | 7 | cargo check | ✅ Compiles |
| Rust STDB reducer tests | ~200 | `#[cfg(test)]` | ✅ In-memory (`__dummy()`) |
| Container integration | auto | `make test-container` | ✅ Spins up STDB Docker container |
| Frontend unit | 52 | vitest + RTL | ✅ 3s |
| E2E (UI) | 33 | Playwright | ✅ 1.1m |
| **Total** | **~144+** | | ✅ |

## Test STDB Container

The `docker-compose.test.yml` and `scripts/run-integration-tests.sh` provide a fully
containerized integration test suite:

```bash
make test-container          # Build WASM + spin up STDB container + run all tests
bash scripts/run-integration-tests.sh --quick   # Skip WASM build, reuse existing
bash scripts/run-integration-tests.sh --no-cleanup  # Keep container for debugging
```

Wired into CI: the `test-container` job in `.github/workflows/test.yml` boots the
STDB container and runs `scripts/run-integration-tests.sh` on every push/PR to main.

**Key differences from dev setup:**
- STDB runs on port **3002** (non-conflicting with dev :3001)
- Ephemeral storage (`tmpfs`) — clean state every run
- Full lifecycle management: start → publish → test → cleanup
