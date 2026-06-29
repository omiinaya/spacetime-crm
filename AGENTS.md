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
4|> Last updated: 2026-06-28
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
18|| PDF | Jinja2 + WeasyPrint (server/templates/) | — |
19|
20|---
21|
22|## 2. Workspace Layout
23|
24|```
25|spacetime-crm/
26|├── server/
27|│   ├── main.py                # FastAPI server — ALL endpoints (~2250 lines)
28|│   ├── config.py              # Pydantic settings (STDB host/port, JWT, Stripe)
29|│   ├── requirements.txt       # Python deps
30|│   ├── Dockerfile             # Multi-stage: frontend build + Python runtime
31|│   ├── mail.py                # Email notification engine
32|│   ├── sms.py                 # Twilio SMS notification engine
33|│   ├── webhooks.py            # HMAC-signed webhook delivery engine
34|│   ├── stripe_payments.py     # Stripe Checkout integration
35|│   ├── templates/             # Jinja2 PDF templates
36|│   └── spacetimedb/           # STDB Rust module
37|│       ├── Cargo.toml         # spacetimedb = "=2.4.0"
38|│       └── src/
39|│           ├── lib.rs         # Module root — table defs + reducers + helpers
40|│           ├── customer.rs    # Customer table + reducers
41|│           ├── ticket.rs      # Ticket + TicketNote + TicketTimer tables
42|│           ├── invoice.rs     # (defined in lib.rs)
43|│           ├── payment.rs     # Payment table + reducers
44|│           ├── appointment.rs # Appointment table + reducers
45|│           ├── product.rs     # Product/inventory table + reducers
46|│           ├── estimate.rs    # (defined in lib.rs)
47|│           ├── purchase_order.rs # PO + POLineItem tables
48|│           ├── user.rs        # User + UserSettings tables
49|│           ├── inventory.rs   # Inventory adjustment table
50|│           ├── tax_rate.rs    # Tax rate configuration
51|│           ├── audit.rs       # Audit log table
52|│           ├── custom_field.rs # Custom fields per entity
53|│           ├── customer_geolocation.rs # Geo-location cache
54|│           ├── checklist.rs   # Repair checklist templates
55|│           └── webhook.rs     # Webhook subscription table
56|├── web/
57|│   ├── src/
58|│   │   ├── App.tsx            # Layout + sidebar + routing
59|│   │   ├── main.tsx           # React entry point
60|│   │   ├── lib/
61|│   │   │   ├── api.ts         # Typed API client (783 lines, all interfaces)
62|│   │   │   ├── auth.tsx       # JWT auth context + provider
63|│   │   │   └── utils.ts       # cn() utility
64|│   │   ├── components/ui/     # Button, Card, Badge, Input, Select, Label
65|│   │   ├── components/        # MonthCalendar, etc.
66|│   │   └── pages/             # One page per domain (see task map below)
67|│   ├── package.json           # Scripts: dev, build, preview
68|│   ├── vite.config.ts         # Port 5185, proxy /api → :8723
69|│   └── index.html
70|├── scripts/
71|│   ├── publish-stdb.sh        # Build + publish STDB module
72|│   ├── docker-entrypoint.sh   # Docker startup (wait for STDB, publish, start API)
73|│   ├── seed-demo.py           # Seed demo data (customers, tickets, invoices...)
74|│   ├── backup.py              # Full STDB backup to .json.gz
75|│   └── restore.py             # Destructive restore from backup
76|├── docker-compose.yml         # spacetime + backend services
77|├── Makefile                   # build, test, lint, fmt, dev-up, clean
78|├── AGENTS.md                  # ← This file
79|├── CLAUDE.md                  # Quick signpost
80|├── CONTRIBUTING.md            # Contribution guidelines
81|├── README.md                  # Project overview + quick start
82|└── ROADMAP.md                 # Phase progress
83|```
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
101|```bash
102|# Start SpacetimeDB
103|spacetime start -l 3001
104|
105|# Publish STDB module (after changing Rust code)
106|cd server/spacetimedb
107|cargo build --release --target wasm32-unknown-unknown
108|spacetime publish -s local-3001 --yes spacetime-crm
109|
110|# Start API server
111|cd server && cp -n .env.example .env 2>/dev/null; python3 main.py
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