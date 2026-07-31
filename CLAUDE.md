# SpacetimeCRM — CLAUDE.md

## Identity
RepairShopr-style CRM built on SpacetimeDB (Rust) + FastAPI (Python) + React/Vite (TypeScript).

## Quick Commands
```bash
# Dev — full stack
make dev-up

# Dev — individual services
spacetime start -l 3001                                 # STDB
cd server && python3 main.py                            # FastAPI (:8723)
cd web && npm run dev                                   # Vite (:5185)

# STDB module
cd server/spacetimedb && cargo build --release --target wasm32-unknown-unknown
spacetime publish -s local-3001 --yes spacetime-crm

# Docker
docker compose up -d                                    # full production stack
```

## Key Paths
| Path | Role |
|------|------|
| `server/main.py` | FastAPI entry point (app wiring, startup; routes live in `server/routes/`) |
| `server/routes/` | One `.py` per domain (customers, tickets, invoices, …) |
| `server/spacetimedb/src/lib.rs` | STDB module root — tables, reducers, helpers |
| `server/spacetimedb/src/*.rs` | One file per domain (customer, ticket, invoice, …) |
| `web/src/pages/` | One `.tsx` per domain page |
| `web/src/lib/api/` | Typed API client (split by domain; `index.ts` re-exports) |
| `web/src/lib/auth.tsx` | JWT auth context + provider |
| `scripts/` | publish-stdb.sh, backup.py, restore.py, seed-demo.py, docker-entrypoint.sh |

## Ports
| Service | Port |
|---------|------|
| SpacetimeDB | 3001 |
| FastAPI backend | 8723 |
| Vite dev server | 5185 |

## Conventions
- **IDs**: auto-generated `{prefix}_{timestamp}_{sender}` format (e.g. `cus_1748500000_a1b2c3d4`)
- **Auth**: JWT in `Authorization: Bearer <token>`, stored in `localStorage("crm_token")`
- **Roles**: `admin`, `tech`, `front_desk` — checked via `require_role()` dependency
- **STDB access**: FastAPI uses raw SQL POST or reducer calls via httpx
- **Audit**: every mutation calls `_log_audit()` (fire-and-forget)
- **Webhooks**: HMAC-SHA256 signed, retry with exponential backoff (3 attempts)
- **Templates**: Jinja2 in `server/templates/` for PDF generation via Playwright/Chromium (replaced WeasyPrint — see `server/pdf.py`)

## Pitfalls
1. **Test suites live in `server/tests/` (pytest) and `web/src/test/` (vitest)** — run them for any change.
2. **STDB wasm builds** require `--target wasm32-unknown-unknown` target installed (`rustup target add wasm32-unknown-unknown`).
3. **STDB SQL limits** — no `IN`/`NOT IN`/`ORDER BY` in raw SQL; sort in Python, use multiple `!=` clauses. See AGENTS.md.
4. **JWT secret** auto-generated on startup if default — but token invalidation means existing sessions break on restart.
5. **Docker build** needs `--network host` for the backend build stage (Rust wasm compile).
6. **Lint config**: `ruff.toml` + `pyproject.toml` for Python, `make lint` for all.
7. **Package manager**: `npm ci` for web, `pip install -r requirements.txt` for server.

## Documentation Index
- [README.md](./README.md) — project overview, quick start, API endpoints, STDB tables
- [AGENTS.md](./AGENTS.md) — full agent onboarding, task-to-file mapping
- [ROADMAP.md](./ROADMAP.md) — phase progress
- [CONTRIBUTING.md](./CONTRIBUTING.md) — contribution guidelines including AI agent section
