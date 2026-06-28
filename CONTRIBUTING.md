# Contributing to SpacetimeCRM

Thank you for your interest in contributing! This document covers both human and AI agent contributors.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Workflow](#development-workflow)
3. [Code Conventions](#code-conventions)
4. [Pull Request Guidelines](#pull-request-guidelines)
5. [AI Agent Contributors](#ai-agent-contributors)
6. [Documentation](#documentation)

---

## Getting Started

1. **Prerequisites**: Rust (with `wasm32-unknown-unknown` target), Node.js >= 18, Python >= 3.10, Docker (optional).
2. **Fork and clone** the repository.
3. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit JWT_SECRET for production
   ```
4. **Install dependencies**:
   ```bash
   cd server && pip install -r requirements.txt
   cd ../web && npm install
   ```
5. **Read the docs**: [README.md](./README.md) for overview, [AGENTS.md](./AGENTS.md) for full onboarding.

## Development Workflow

1. **Start SpacetimeDB**: `spacetime start -l 3001`
2. **Publish the STDB module**: `cd server/spacetimedb && cargo build --release --target wasm32-unknown-unknown && spacetime publish -s local-3001 --yes spacetime-crm`
3. **Start the backend**: `cd server && python3 main.py` (or `uvicorn main:app --reload`)
4. **Start the frontend**: `cd web && npm run dev`
5. **Open**: http://localhost:5185

For quick access, use the Makefile:
```bash
make dev-up     # prints commands to start all services
make build      # builds STDB + frontend
make publish-stdb  # build + publish STDB module
make seed       # seed demo data
```

## Code Conventions

### Rust (STDB module — `server/spacetimedb/`)
- Follow existing patterns in `customer.rs`, `ticket.rs`, etc.
- One file per domain with `pub use` in `lib.rs`.
- Reducer names: `create_{entity}`, `update_{entity}`, `delete_{entity}`, `add_{entity}_line_item`.
- ID format: `{prefix}_{timestamp}_{sender_short}` (e.g. `cus_1748500000_a1b2c3d4`).

### Python (FastAPI — `server/main.py`)
- **No linting/formatting config exists yet**. Use `ruff` if installed.
- All endpoints live in `server/main.py` (single file, ~2250 lines).
- Auth: use `require_role("admin", "tech", "front_desk")` dependency.
- Every mutation must call `_log_audit()` and `_fire_webhook()`.
- Helper functions: `_sql()` for raw queries, `_call()` for reducers, `_sort()` for ordered results.
- Status quo: All routes are async defs with httpx for STDB communication.

### TypeScript/React (`web/`)
- Pages: one `.tsx` per domain in `web/src/pages/`.
- Components: shared UI in `web/src/components/ui/`.
- API client: `web/src/lib/api.ts` — typed fetch wrapper.
- Auth: `web/src/lib/auth.tsx` — React context + JWT management.
- Token stored in `localStorage("crm_token")`.
- Vite proxy: `/api` → `http://127.0.0.1:8723` (configured in `vite.config.ts`).

### General
- **No test suite exists** — contributions including tests are highly valued.
- **Commit messages**: Conventional Commits format (`feat:`, `fix:`, `docs:`, etc.).
- **Branch naming**: `feature/description`, `fix/description`, `docs/description`.

## Pull Request Guidelines

1. Create a feature branch from `main`.
2. Keep PRs focused on a single concern.
3. Update documentation if you change API behavior or add features.
4. Verify the STDB module compiles: `cargo build --release --target wasm32-unknown-unknown`.
5. Verify the frontend compiles: `cd web && npx tsc --noEmit`.
6. If you add/modify an API endpoint, update the endpoint table in README.md.
7. If you add/modify an STDB table, update the table list in README.md.

## AI Agent Contributors

This section provides guidance for AI coding agents (Claude Code, Codex, Cursor, etc.) working on SpacetimeCRM.

### Onboarding

AI agents should begin by reading these files in order:
1. **README.md** — project overview and quick start.
2. **AGENTS.md** — full agent onboarding, task-to-file mapping, system architecture.
3. **CLAUDE.md** — quick reference signpost.
4. **Makefile** — available commands.

### Task-to-File Mapping

| Task | Primary Files |
|------|---------------|
| Add/modify a domain (customer, ticket, etc.) | `server/spacetimedb/src/{domain}.rs`, `server/main.py` (endpoints), `web/src/pages/{Domain}Page.tsx`, `web/src/lib/api.ts` (types) |
| Change auth logic | `server/main.py` (require_role), `web/src/lib/auth.tsx`, `web/src/lib/api.ts` |
| Add/modify STDB table/reducer | `server/spacetimedb/src/{domain}.rs`, register in `lib.rs` |
| Add API endpoint | `server/main.py` (route + _call/_sql), README.md table, `web/src/lib/api.ts` |
| Add frontend page | `web/src/pages/{Domain}Page.tsx`, register in `web/src/App.tsx` |
| Add notification channel | `server/mail.py`, `server/sms.py` + corresponding modules |
| Modify Docker/deployment | `docker-compose.yml`, `server/Dockerfile`, `scripts/docker-entrypoint.sh` |
| Add backup/restore logic | `scripts/backup.py`, `scripts/restore.py` |
| Add webhook event | `server/webhooks.py` (event constant), `server/main.py` (fire call in endpoint) |

### Constraints AI Agents Must Follow

1. **Never fabricate test results or API responses.** If a tool fails, report the blocker honestly.
2. **Validate STDB wasm builds** — ensure `wasm32-unknown-unknown` target is installed.
3. **Check for existing PRs** in the knowledge graph before starting work (use `mcp_graphify_list_prs` if available).
4. **Update docs** as part of every PR — README endpoint tables, AGENTS.md task mapping if new domains are added.
5. **Follow ID conventions**: auto-generated IDs in STDB reducers, not client-supplied IDs.
6. **Every mutation needs audit logging and webhook fire** — see existing patterns in `server/main.py`.
7. **Do not modify `server/spacetimedb/src/lib.rs`** unless adding a new module (add `mod {}` + `pub use`).
8. **Respect the existing architecture**: FastAPI routes → `_sql()` or `_call()` → STDB reducers. No ORM, no direct DB connections.

### Useful Commands for Agents

```bash
# Build STDB module (after changes to Rust files)
cargo build --release --target wasm32-unknown-unknown --manifest-path server/spacetimedb/Cargo.toml

# Type-check frontend
cd web && npx tsc --noEmit

# Check Python syntax
python3 -m py_compile server/main.py

# Seed demo data (requires running backend)
python3 scripts/seed-demo.py
```

## Documentation

All documentation files live in the project root:

| File | Purpose |
|------|---------|
| [README.md](./README.md) | Project overview, quick start, API endpoints, STDB tables |
| [AGENTS.md](./AGENTS.md) | Full agent onboarding, task-to-file mapping |
| [CLAUDE.md](./CLAUDE.md) | Quick signpost for Claude/Codex agents |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | This file |
| [ROADMAP.md](./ROADMAP.md) | Phase progress and completed features |
| [MAKEFILE](./Makefile) | Build, test, lint, fmt, dev commands |
