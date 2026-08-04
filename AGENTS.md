---
name: SpacetimeCRM
description: "RepairShopr-inspired CRM built on SpacetimeDB — customers, tickets, invoicing, appointments"
stack: [python, fastapi, react, typescript, spacetimedb]
ports:
  frontend: 5185
  stdb: 3001
deps: [python3, node, npm]
stdb: true
---

1|# SpacetimeCRM — AGENTS.md
2|
3|> Full agent onboarding guide. Read this before making changes to the codebase.
4|> Last updated: 2026-07-31
5|
6|---
7|
8|## 1. Identity & Stack
9|
10|SpacetimeCRM is a RepairShopr-style CRM built for small repair shops. It manages customers, repair tickets, invoices, payments, appointments, inventory, estimates, and purchase orders.
11|
12|| Layer | Technology | Port |
13||-------|-----------|------|
14|| Database | SpacetimeDB (Rust module, wasm target) | 3001 |
15|| Backend API | FastAPI (Python, single-file server) | 8723 |
16|| Frontend | React 18 + Vite 6 + TailwindCSS v4 + shadcn-style | 5185 |
17|| Auth | JWT (HS256, stored in localStorage) | — |
18|| PDF | Jinja2 + Playwright/Chromium (server/pdf.py) | — |
19|
20|---
21|
22|## 2. Workspace Layout
23|
```
spacetime-crm/
├── server/
│   ├── main.py                # FastAPI entrypoint — mounts routers (~109 lines)
│   ├── routes/                # 25 route modules (auth, customers, tickets, invoices,
│   │   │                      #   payments, appointments, products, estimates, POS,
│   │   │                      #   purchase_orders, reports, portal, gift_cards, ...)
│   ├── config.py              # Pydantic settings (STDB host/port, JWT, Stripe)
│   ├── requirements.txt       # Python deps
│   ├── Dockerfile             # Multi-stage: frontend build + Python runtime
│   ├── helpers.py             # _sql/_call/_require_owned/_sqlesc/audit/webhook helpers
│   ├── mail.py                # Email notification engine
│   ├── sms.py                 # Twilio SMS notification engine
│   ├── pdf.py                 # Jinja2 + Playwright PDF generation
│   ├── stripe_payments.py     # Stripe Checkout integration
│   ├── templates/             # Jinja2 PDF templates
│   └── spacetimedb/           # STDB Rust module
│       ├── Cargo.toml         # spacetimedb = "=2.4.0"
│       └── src/
│           ├── lib.rs         # Module root — table defs + reducers + helpers
│           ├── customer.rs    # Customer table + reducers
│           ├── ticket.rs      # Ticket + TicketNote + TicketTimer tables
│           ├── invoice.rs     # Invoice + line items + reducers
│           ├── payment.rs     # Payment table + reducers
│           ├── appointment.rs # Appointment table + reducers
│           ├── product.rs     # Product/inventory table + reducers
│           ├── estimate.rs    # Estimate + line items + reducers
│           ├── purchase_order.rs # PO + POLineItem tables
│           ├── recurring_invoice_rule.rs # Recurring invoice rules
│           ├── gift_card.rs   # Gift cards
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
│   │   ├── App.tsx            # Layout + sidebar + routing (~550 lines)
│   │   ├── main.tsx           # React entry point
│   │   ├── lib/
│   │   │   ├── api/           # Typed API client — one module per domain (25 files)
│   │   │   ├── auth.tsx       # JWT auth context + provider
│   │   │   ├── portal-auth.ts # Customer portal auth
│   │   │   ├── theme.ts       # Dark/light theme + localStorage persistence
│   │   │   ├── useNetworkStatus.ts # Offline detection
│   │   │   └── utils.ts       # cn() utility
│   │   ├── components/ui/     # Button, Card, Badge, Input, Select, Label
│   │   ├── components/        # MonthCalendar, etc.
│   │   ├── pages/             # 32 pages — one per domain (see task map below)
│   │   └── test/              # Vitest suites: 259 tests (pages/ + components/ + lib/)
│   ├── e2e/                   # Playwright specs (~100 tests, see E2E section below)
│   ├── package.json           # Scripts: dev, build, preview, test
│   ├── vite.config.ts         # Port 5185, proxy /api → :8723, PWA plugin
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
84|
85|---
86|
87|## 3. Quick Reference
88|
89|### Ports & URLs
90|
91|| Service | URL |
92||---------|-----|
93|| SpacetimeDB | http://localhost:3001 |
94|| FastAPI backend | http://localhost:8723 |
95|| FastAPI docs | http://localhost:8723/docs |
96|| Vite dev frontend | http://localhost:5185 |
97|| Docker compose backend | http://localhost:8723 |
98|
99|### Essential Commands
100|
```bash
# Start SpacetimeDB
spacetime start -l 3001

# Publish STDB module (after changing Rust code)
cd server/spacetimedb
cargo build --release --target wasm32-unknown-unknown
spacetime publish -s local-3001 --yes spacetime-crm

# After publish with --delete-data, re-bootstrap:
python3 scripts/bootstrap.py  # creates admin user + tenant
python3 scripts/seed-demo.py   # seeds demo data
# Or combined:
bash scripts/reseed.sh

# Start API server
cd server && cp -n .env.example .env 2>/dev/null; python3 main.py
112|
113|# Start frontend dev server
114|cd web && npm run dev
115|
116|# Docker production stack
117|docker compose up -d
118|```
119|
120|### Makefile Targets
121|
122|```bash
123|make build          # STDB wasm + frontend dist
124|make lint           # Run all linters
125|make fmt            # Format all code
126|make fix            # Auto-fix lint issues
127|make dev-up         # Print instructions to start all dev services
128|make dev-down       # Kill dev processes
129|make clean          # Remove all build artifacts
130|make publish-stdb   # Build & publish STDB module to local
131|make seed           # Seed demo data
132|make backup         # Backup STDB data
133|```
134|
135|---
136|
137|## 4. Architecture: How Data Flows
138|
139|```
140|Browser (React)
141|    │
142|    │  HTTP /api/*  (Vite proxy → :8723)
143|    ▼
144|FastAPI (server/main.py)
145|    │
146|    ├─ _sql("SELECT * FROM ...")  → POST /v1/database/{db}/sql   → STDB
147|    └─ _call("reducer_name", [])  → POST /v1/database/{db}/call  → STDB
148|         │
149|         ▼
150|    SpacetimeDB (Rust module)
151|         │
152|         ├─ Tables (public, auto-persisted)
153|         └─ Reducers (mutations with audit + webhook triggers)
154|```
155|
156|Key rules:
157|- **No ORM.** FastAPI communicates with STDB via raw HTTP (httpx).
158|- **No direct DB connections.** Every STDB interaction goes through `_sql()` or `_call()`.
159|- **IDs are auto-generated** by STDB reducers using `make_id(prefix, ctx)` → `{prefix}_{unix_ms}_{sender_short}`.
160|- **Auth is JWT-based.** `require_role("admin", "tech", "front_desk")` decorator on every endpoint.
161|- **Every mutation audits.** `_log_audit()` is fire-and-forget — never raises.
162|- **Every entity event fires webhooks.** `_fire_webhook()` via `asyncio.ensure_future()`.
163|


## 5. E2E Testing (Playwright)

Located in `web/e2e/`. Run with `npm run test:e2e` (or `npx playwright test` from `web/`).

- **Auth:** tests inject a fake JWT into `localStorage` (`e2e/helpers.ts` -> `loginAs()`), so the app boots authenticated but every API call 401s. Tests are **UI-structure + interaction** tests (headings, buttons, filters, overlays, tabs, navigation) — they never mutate data. Real CRUD is covered by backend pytest + vitest.
- **Config** (`playwright.config.ts`): `workers: 1`, `timeout: 90000` — single worker avoids Vite dev-server degradation; see `e2e/_warmup.spec.ts` which pre-compiles every heavy page to avoid cold-start timeouts.
- **Navigation helpers:** `navTo(page, label)` (sidebar), `navToSubTab(page, parent, sub)` (sub-tab pages), `navToSettingsTab(page, tab)` (Settings tabs).
- **One spec per page/domain** — add a spec when adding a page.

## 6. Navigation Architecture

The sidebar is **grouped** (`web/src/App.tsx`, `navSections`) — 13 top-level items in labeled sections (Sales, Scheduling, Inventory, Point of Sale, Marketing, Insights, Administration). Secondary pages are **not** top-level:

| Page | Lives at |
|------|----------|
| Map | Customers -> **Map** sub-tab (`SUB_TABS`) |
| Recurring invoices | Invoices -> **Recurring** sub-tab |
| Payment Methods | Payments -> **Payment Methods** sub-tab |
| Gift Cards | Payments -> **Gift Cards** sub-tab |
| Tech Schedule | Appointments -> **Tech Schedule** sub-tab |
| Import/Export, Custom Fields, Audit Log | Settings -> **Data & Fields** tab |
| Checklists, Health, Tenants, Agent Access | Settings -> **System** tab |

- `SUB_TABS` (App.tsx) maps a parent page to its sub-tabs; `SUB_TAB_PARENT` maps sub-page ids back to their parent so the tab bar stays visible. `isNavVisible(id, role)` is the single source of truth for role-based visibility (sidebar items and sub-tabs).
- **When adding a page:** keep the `PageId` union (`src/lib/navigation.ts`) + the App.tsx switch case, then decide: top-level sidebar item, sub-tab under a parent, or a Settings tab.
- Settings (`SettingsPage.tsx`) is tabbed: General / Notifications / Business / Data & Fields / System.
