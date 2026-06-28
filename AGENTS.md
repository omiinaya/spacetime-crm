# SpacetimeCRM — AGENTS.md

> Full agent onboarding guide. Read this before making changes to the codebase.
> Last updated: 2026-06-28

---

## 1. Identity & Stack

SpacetimeCRM is a RepairShopr-style CRM built for small repair shops. It manages customers, repair tickets, invoices, payments, appointments, inventory, estimates, and purchase orders.

| Layer | Technology | Port |
|-------|-----------|------|
| Database | SpacetimeDB (Rust module, wasm target) | 3001 |
| Backend API | FastAPI (Python, single-file server) | 8723 |
| Frontend | React 18 + Vite 6 + TailwindCSS v4 + shadcn-style | 5185 |
| Auth | JWT (HS256, stored in localStorage) | — |
| PDF | Jinja2 + WeasyPrint (server/templates/) | — |

---

## 2. Workspace Layout

```
spacetime-crm/
├── server/
│   ├── main.py                # FastAPI server — ALL endpoints (~2250 lines)
│   ├── config.py              # Pydantic settings (STDB host/port, JWT, Stripe)
│   ├── requirements.txt       # Python deps
│   ├── Dockerfile             # Multi-stage: frontend build + Python runtime
│   ├── mail.py                # Email notification engine
│   ├── sms.py                 # Twilio SMS notification engine
│   ├── webhooks.py            # HMAC-signed webhook delivery engine
│   ├── stripe_payments.py     # Stripe Checkout integration
│   ├── templates/             # Jinja2 PDF templates
│   └── spacetimedb/           # STDB Rust module
│       ├── Cargo.toml         # spacetimedb = "=2.4.0"
│       └── src/
│           ├── lib.rs         # Module root — table defs + reducers + helpers
│           ├── customer.rs    # Customer table + reducers
│           ├── ticket.rs      # Ticket + TicketNote + TicketTimer tables
│           ├── invoice.rs     # (defined in lib.rs)
│           ├── payment.rs     # Payment table + reducers
│           ├── appointment.rs # Appointment table + reducers
│           ├── product.rs     # Product/inventory table + reducers
│           ├── estimate.rs    # (defined in lib.rs)
│           ├── purchase_order.rs # PO + POLineItem tables
│           ├── user.rs        # User + UserSettings tables
│           ├── inventory.rs   # Inventory adjustment table
│           ├── tax_rate.rs    # Tax rate configuration
│           ├── audit.rs       # Audit log table
│           ├── custom_field.rs # Custom fields per entity
│           ├── customer_geolocation.rs # Geo-location cache
│           ├── checklist.rs   # Repair checklist templates
│           └── webhook.rs     # Webhook subscription table
├── web/
│   ├── src/
│   │   ├── App.tsx            # Layout + sidebar + routing
│   │   ├── main.tsx           # React entry point
│   │   ├── lib/
│   │   │   ├── api.ts         # Typed API client (783 lines, all interfaces)
│   │   │   ├── auth.tsx       # JWT auth context + provider
│   │   │   └── utils.ts       # cn() utility
│   │   ├── components/ui/     # Button, Card, Badge, Input, Select, Label
│   │   ├── components/        # MonthCalendar, etc.
│   │   └── pages/             # One page per domain (see task map below)
│   ├── package.json           # Scripts: dev, build, preview
│   ├── vite.config.ts         # Port 5185, proxy /api → :8723
│   └── index.html
├── scripts/
│   ├── publish-stdb.sh        # Build + publish STDB module
│   ├── docker-entrypoint.sh   # Docker startup (wait for STDB, publish, start API)
│   ├── seed-demo.py           # Seed demo data (customers, tickets, invoices...)
│   ├── backup.py              # Full STDB backup to .json.gz
│   └── restore.py             # Destructive restore from backup
├── docker-compose.yml         # spacetime + backend services
├── Makefile                   # build, test, lint, fmt, dev-up, clean
├── AGENTS.md                  # ← This file
├── CLAUDE.md                  # Quick signpost
├── CONTRIBUTING.md            # Contribution guidelines
├── README.md                  # Project overview + quick start
└── ROADMAP.md                 # Phase progress
```

---

## 3. Quick Reference

### Ports & URLs

| Service | URL |
|---------|-----|
| SpacetimeDB | http://localhost:3001 |
| FastAPI backend | http://localhost:8723 |
| FastAPI docs | http://localhost:8723/docs |
| Vite dev frontend | http://localhost:5185 |
| Docker compose backend | http://localhost:8723 |

### Essential Commands

```bash
# Start SpacetimeDB
spacetime start -l 3001

# Publish STDB module (after changing Rust code)
cd server/spacetimedb
cargo build --release --target wasm32-unknown-unknown
spacetime publish -s local-3001 --yes spacetime-crm

# Start API server
cd server && cp -n .env.example .env 2>/dev/null; python3 main.py

# Start frontend dev server
cd web && npm run dev

# Docker production stack
docker compose up -d
```

### Makefile Targets

```bash
make build          # STDB wasm + frontend dist
make lint           # Run all linters
make fmt            # Format all code
make fix            # Auto-fix lint issues
make dev-up         # Print instructions to start all dev services
make dev-down       # Kill dev processes
make clean          # Remove all build artifacts
make publish-stdb   # Build & publish STDB module to local
make seed           # Seed demo data
make backup         # Backup STDB data
```

---

## 4. Architecture: How Data Flows

```
Browser (React)
    │
    │  HTTP /api/*  (Vite proxy → :8723)
    ▼
FastAPI (server/main.py)
    │
    ├─ _sql("SELECT * FROM ...")  → POST /v1/database/{db}/sql   → STDB
    └─ _call("reducer_name", [])  → POST /v1/database/{db}/call  → STDB
         │
         ▼
    SpacetimeDB (Rust module)
         │
         ├─ Tables (public, auto-persisted)
         └─ Reducers (mutations with audit + webhook triggers)
```

Key rules:
- **No ORM.** FastAPI communicates with STDB via raw HTTP (httpx).
- **No direct DB connections.** Every STDB interaction goes through `_sql()` or `_call()`.
- **IDs are auto-generated** by STDB reducers using `make_id(prefix, ctx)` → `{prefix}_{unix_ms}_{sender_short}`.
- **Auth is JWT-based.** `require_role("admin", "tech", "front_desk")` decorator on every endpoint.
- **Every mutation audits.** `_log_audit()` is fire-and-forget — never raises.
- **Every entity event fires webhooks.** `_fire_webhook()` via `asyncio.ensure_future()`.
