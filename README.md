# SpacetimeCRM

RepairShopr-inspired CRM built on SpacetimeDB — customers, tickets, invoicing, appointments, inventory, estimates, and purchase orders.

## Stack

- **Backend**: SpacetimeDB (Rust module) + FastAPI (Python)
- **Frontend**: React 18 + Vite 6 + TailwindCSS v4 + shadcn-style components + Lucide icons
- **Database**: SpacetimeDB (local:3001)

## Documentation

| File | Purpose |
|------|---------|
| [README.md](./README.md) | This file — project overview, quick start, API endpoints, STDB tables |
| [AGENTS.md](./AGENTS.md) | Full agent onboarding — task-to-file mapping, architecture, pitfalls |
| [CLAUDE.md](./CLAUDE.md) | Quick signpost for Claude/Codex AI agents |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Contribution guidelines (human + AI agent) |
| [ROADMAP.md](./ROADMAP.md) | Phase progress and completed features |
| [Makefile](./Makefile) | Build, test, lint, fmt, dev commands |

## Project Structure

```
spacetime-crm/
├── server/
│   ├── spacetimedb/           # SpacetimeDB Rust module
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs         # Module exports + helpers
│   │       ├── customer.rs    # Customer table + reducers
│   │       ├── ticket.rs      # Ticket + TicketNote + TicketTimer
│   │       ├── invoice.rs     # Invoice + InvoiceLineItem
│   │       ├── payment.rs     # Payment table + reducers
│   │       ├── appointment.rs # Appointment table + reducers
│   │       ├── product.rs     # Product table + reducers
│   │       ├── estimate.rs    # Estimate + EstimateLineItem
│   │       ├── purchase_order.rs # PO + POLineItem
│   │       └── user.rs        # User + UserSettings
│   ├── main.py                # FastAPI REST server (port 8723)
│   ├── config.py              # Pydantic settings
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── web/
│   ├── src/
│   │   ├── App.tsx            # Layout + sidebar + routing
│   │   ├── lib/
│   │   │   ├── api.ts         # Typed API client
│   │   │   └── utils.ts       # cn() utility
│   │   ├── components/ui/     # Card, Button, Badge, Input, Select
│   │   └── pages/             # One page per domain
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── tsconfig.json
├── deploy/
│   ├── nginx/
│   │   ├── spacetime-crm.conf   # Nginx reverse proxy + TLS config
│   │   └── deploy.sh            # One-command nginx deploy script
│   ├── docker-compose.prod.yml  # Production overrides (resource limits, nginx)
│   └── .env.prod.example        # Production env template (CORS, JWT, SMTP, etc.)
├── README.md
├── ROADMAP.md
├── IMPROVEMENTS.md
└── .gitignore
```

## Quick Start

### 1. Start SpacetimeDB

```bash
spacetime start -l 3001
```

### 2. Publish the module (manual)

```bash
cd server/spacetimedb
spacetime publish -s local-3001 --yes spacetime-crm
```

### 3. Start the API server

```bash
cd server
cp .env.example .env
pip install -r requirements.txt
python3 main.py
```

### 4. Start the frontend dev server

```bash
cd web
npm install
npm run dev
```

Open http://localhost:5185

---

## 🐳 Docker Compose Production

### Quick start (dev-mode Docker, no TLS)

```bash
cp .env.example .env
# Edit .env to set JWT_SECRET (required for production)

# Optional: pre-build STDB module so backend auto-publishes on start
cd server/spacetimedb
cargo build --release --target wasm32-unknown-unknown
cd ../..

# Start everything
docker compose up -d
```

Open http://localhost:8723

### Production with nginx reverse proxy + TLS

```bash
# 1. Copy and fill in production env (sets CORS, APP_URL, etc.)
cp deploy/.env.prod.example .env
# Edit .env — set JWT_SECRET to a long random string

# 2. Build STDB module (required for auto-publish)
cd server/spacetimedb
cargo build --release --target wasm32-unknown-unknown
cd ../..

# 3. Deploy nginx config with self-signed TLS cert
sudo bash deploy/nginx/deploy.sh

# 4. Start the stack with production overrides
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d
```

Open https://192.168.1.10 (or your configured domain)

> ⚠️ Self-signed TLS produces a browser warning — expected for local/testing.
> For production with a real domain:
> ```bash
> sudo certbot --nginx -d your-domain.com
> ```

### What happens:

1. **SpacetimeDB** starts on port 3001
2. **Backend** waits for STDB to be healthy, then starts FastAPI serving API + pre-built React frontend on port 8723
3. If a pre-built `.wasm` module was included at build time, the entrypoint auto-publishes it

### Stop:

```bash
docker compose down
# To also remove STDB data:
docker compose down -v
```

### Manual STDB module publish:

```bash
./scripts/publish-stdb.sh [database_name]
```

---

## 💾 Backup & Restore

### Backup all data:

```bash
python3 scripts/backup.py
# Saved to ./backups/spacetime-crm-backup-<timestamp>.json.gz
```

Dumps all 18 STDB tables to a compressed JSON snapshot.

### Restore from backup:

```bash
# 1. Build the STDB module first
cd server/spacetimedb
cargo build --release --target wasm32-unknown-unknown
cd ../..

# 2. Run restore (will delete + re-publish database!)
python3 scripts/restore.py backups/spacetime-crm-backup-<timestamp>.json.gz
```

⚠️  Restore is destructive — it deletes the existing database, re-publishes the module, and re-inserts records. Tables with `import_*` reducers (customer, product) preserve their IDs. Other tables use their create reducers (new IDs generated). A manual password/settings restore may be needed.

---

## API Endpoints

| Domain | Endpoints |
|--------|-----------|
| **Stats** | `GET /api/stats` |
| **Customers** | `GET/POST /api/customers`, `PUT/DELETE /api/customers/:id` |
| **Tickets** | `GET/POST /api/tickets`, `PUT /api/tickets/:id/status`, `PUT /api/tickets/:id/assign`, notes CRUD |
| **Invoices** | `GET/POST /api/invoices`, status updates, line item CRUD |
| **Payments** | `GET/POST /api/payments`, `DELETE /api/payments/:id` |
| **Appointments** | `GET/POST /api/appointments`, status updates, delete |
| **Products** | `GET/POST /api/products`, quantity updates, delete |
| **Estimates** | `GET/POST /api/estimates`, status updates, line item CRUD |
| **Purchase Orders** | `GET/POST /api/purchase-orders`, delete |
| **Users** | `GET/POST /api/users` |
| **Roles** | `require_role()` middleware protects all admin/staff endpoints |
| **Audit Log** | `GET /api/audit-log` (admin only) |
| **CSV Export** | `GET /api/export/{entity}` (customers, tickets, invoices, etc.) |
| **CSV Import** | `POST /api/import/customers`, `POST /api/import/products` |
| **Webhooks** | `GET/POST /api/webhook-subscriptions`, `PUT/DELETE /api/webhook-subscriptions/:id`, `POST /api/webhook-subscriptions/:id/test` |
| **Push** | `POST /api/push/subscribe`, `/api/push/unsubscribe`, `/api/push/test` |

## SpacetimeDB Tables

- **customer** — contact info, addresses, notes, tags
- **ticket** — repair tickets with status/priority workflow, device info
- **ticket_note** — internal/external notes on tickets
- **ticket_timer** — time tracking per ticket
- **invoice** — billing with line items, tax, discounts
- **invoice_line_item** — individual chargeable items
- **payment** — payment records against invoices
- **appointment** — scheduled service appointments
- **product** — inventory items with stock levels
- **estimate** — service quotes/estimates
- **estimate_line_item** — individual items on estimates
- **purchase_order** — vendor purchase orders
- **purchase_order_line_item** — items on POs
- **audit_log** — immutable audit trail of all CRUD operations
- **user** — staff accounts with roles
- **user_settings** — per-user preferences
- **push_subscription** — browser push notification subscriptions (VAPID)
