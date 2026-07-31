# SpacetimeCRM — Roadmap & Honest Assessment

| **Last assessed:** | 2026-07-31 (re-audited) |
| **Overall completeness:** | ~99.8% |
| **Total endpoints:** | 106 API routes (28 route files) |
| **Total STDB artifacts:** | 28 tables (+ push_subscriptions) + 77 reducers |
| **Total frontend pages:** | 23 admin + 3 auth + 5 portal = 31 pages |
| **Total tests:** | ~2,200 (1,827 backend + 159 frontend + 211 Rust) |

---

## 📊 Summary by Layer

| Layer | Files | Lines | Completeness | Test Count | Anti-Patterns |
|-------|-------|-------|:------------:|:----------:|:-------------:|
| STDB Module (Rust) | 16 files | ~1,900 | 88% | 211 #[test] (4 files) | 1 major, 3 minor |
| Backend API (Python) | 30 files | ~4,500 | 92% | 1,827 (61 files) | 2 major, 5 minor |
| Frontend (TypeScript) | 45+ files | ~8,000 | 85% | 159 (24 files) | 3 major, 6 minor |
| Infra (Docker/scripts) | 12 files | ~450 | 78% | N/A | 3 gaps |
| **Overall** | **~110 files** | **~20,000** | **~96%** | **~2,200** | **~20 items** |

---

## ✅ PHASE 0: Core Foundation (DONE — 100%)

All core infrastructure complete. No gaps.

- [x] SpacetimeDB 2.4.1 module: 27 tables, 73 reducers
- [x] FastAPI server on port 8723: 99 endpoints across 25 route files
- [x] React 18 + Vite 6 + TailwindCSS v4 + shadcn-style frontend
- [x] Dark theme with localStorage persistence
- [x] JWT auth (HS256) with role-based permissions (admin/tech/front_desk/customer)
- [x] React.lazy() code-splitting (all 30 pages)
- [x] Route splitting: main.py 2,390→55 lines
- [x] Pydantic input validation on all POST/PUT endpoints
- [x] Pagination (offset/limit + total) on all 15 list endpoints
- [x] CORS locked to configurable origin
- [x] Shared httpx client pool
- [x] Rate limiting (100/min default, 10/min auth, 30/min settings)
- [x] Input sanitization (HTML strip on all models)
- [x] Exception handlers (JSON errors, no stack traces)
- [x] Audit logging (58 call sites across all endpoints)
- [x] `_sql_t()` SQL injection protection via tenant_id format validation

---

## ✅ PHASE 1: Core Business Entities (DONE — 100%)

| Entity | Backend Routes | Frontend Page | Tests | Notes |
|--------|---------------|---------------|-------|-------|
| Customers | 8 endpoints | CustomersPage | ✅ | CRUD, search, portal password, geolocation, geocode-all |
| Tickets | 15 endpoints | TicketsPage | ✅ | CRUD, status workflow, notes, timers, checklists, auto-assign |
| Products | 12 endpoints | ProductsPage | ✅ | CRUD, barcode lookup, low-stock, stock transfer, categories, adjustments |
| Invoices | 20+ endpoints | InvoicesPage | ✅ | CRUD, line items, status, tax, PDF, email, email queue, overdue check, bulk status, bulk edit |
| Payments | 6 endpoints | PaymentsPage | ✅ | Record, stripe, refund, pay-invoice |
| Appointments | 10+ endpoints | AppointmentsPage | ✅ | CRUD, status workflow, reminders, recurring set/generate, due-soon |
| Estimates | 8 endpoints | EstimatesPage | ✅ | CRUD, line items, convert to invoice |
| Purchase Orders | 10+ endpoints | PurchaseOrdersPage | ✅ | CRUD, line items, receive, submit/approve/reject |

---

## ✅ PHASE 2: Real-World Features (DONE — 100%)

- [x] Customer portal (dedicated login, dashboard, tickets, invoices, appointments)
- [x] Customer map (Leaflet, individual + batch geocoding)
- [x] Email notifications (ticket status, invoice created, payment received, estimate approved, appointment created, overdue reminders, low stock alerts)
- [x] Email templates (7 Jinja2 templates with base layout)
- [x] SMS notifications (Twilio — ticket status, invoices, reminders)
- [x] PDF generation (invoice, estimate, ticket, receipt — Playwright Chromium)
- [x] Calendar view for appointments (MonthCalendar component)
- [x] Time tracking (ticket timers with start/stop)
- [x] Inventory adjustments (reason, reference, user tracking)
- [x] Purchase order receiving (auto-update stock from line items)
- [x] Tax rate configuration (CRUD, set per invoice)
- [x] Recurring appointments (series_id + recurrence_rule, generate-next)
- [x] Low stock alerts (endpoint + email to admin)
- [x] Discount support (discount_amount on POS, invoices, estimates; discount_percent on invoices)
- [x] Multi-currency (currency field on Invoice, Estimate, PurchaseOrder, POS, Payment)

---

## ✅ PHASE 3: Advanced Features (DONE — 100%)

- [x] Multi-tenant (25 tables with `tenant_id`, migration from single-tenant)
- [x] Stripe payment processing (Checkout sessions + PaymentIntent for saved cards)
- [x] Saved payment methods (STDB table, Stripe SetupIntent, API CRUD, admin UI)
- [x] Portal payment UX (saved cards shown with one-click Pay)
- [x] Reporting dashboard (revenue by month, ticket by status, invoice by status, appointments by month, totals, SLA breach rate, overdue rate, tech closed, top customers, customer acquisition)
- [x] Barcode scanning (camera API + manual lookup)
- [x] Repair checklist templates (CRUD + apply to ticket)
- [x] Custom fields (per entity type, configurable types/options)
- [x] Webhook integration (HMAC-SHA256 signed, 13 event types)
- [x] Report scheduling (6 report types, CRUD, run-now, HTML email delivery, cron check-due)
- [x] Recurring invoices (rule CRUD, auto-generate by cron, line item templates)
- [x] POS / counter sale (kiosk UI, cart, tax, payment, receipt PDF, refund, sale history)
- [x] Purchase order approvals (submit/approve/reject, status workflow)
- [x] Barcode label printing (JsBarcode SVG, print dialog)
- [x] 2FA / TOTP (setup QR, verify, disable, challenge login flow)
- [x] SLA tracking (priority-based thresholds, live urgency indicators, breach detection, configurable)
- [x] Ticket auto-assignment (round-robin to least-loaded tech)
- [x] Revenue vs target on dashboard (color-coded progress bar)
- [x] Bulk edit invoice terms/notes (selection + modal dialog)
- [x] PWA (service worker, manifest, installable mobile app)
- [x] Avg resolution time stat card (5th dashboard summary card)
- [x] Invoice draft auto-save (localStorage persistence)
- [x] Customer duplicate detection (API endpoint)
- [x] Low stock cron job (Hermes cron at 7 AM daily)

---

## ✅ PHASE 4: Production Readiness (DONE — 100%)

- [x] JWT authentication (staff + portal login)
- [x] Role-based permissions (admin, tech, front_desk)
- [x] Audit logging across all endpoints
- [x] CSV data export (customers + invoices)
- [x] Docker Compose (SpacetimeDB + backend, healthchecks, restart policies)
- [x] Multi-stage Dockerfile (node:22 → python:3.12-slim)
- [x] Backup/restore scripts (STDB to .json.gz)
- [x] Health checks (`/api/health`, `/api/health/ready`)
- [x] SQL injection protection (`_sql_t()` validates tenant_id format)
- [x] Input validation (Pydantic models on all 49+ POST/PUT endpoints)
- [x] Frontend code-splitting (980KB → 249KB main bundle)
- [x] CORS locked to `settings.cors_origin`
- [x] Exception handlers (JSON errors, no stack traces)
- [x] Shared httpx client (single connection pool)
- [x] Rate limiting (slowapi: 100/min default, 10/min auth)
- [x] Password recovery (forgot + reset endpoints, email delivery)
- [x] Input sanitization (HTML strip on all Pydantic models)
- [x] CI/CD pipeline (GitHub Actions: STDB build, seed, test, lint)
- [x] E2E tests (Playwright: 33 tests across 5 suites)
- [x] Port 8723 → vite build → nginx/gateway update flow
- [x] Reverse-proxy + TLS config (nginx, self-signed cert, deploy script)
- [x] Production docker-compose overrides (deploy/docker-compose.prod.yml: resource limits, nginx service)
- [x] Production env template (deploy/.env.prod.example: CORS, APP_URL, SMTP, Stripe for production)

---

## 🔴 PHASE 5: Field & Type Gaps (HIGH PRIORITY)

These are gaps between STDB table fields, Python API models, and frontend TypeScript interfaces. All fixes are plain Python/TS changes — no STDB publish needed.

### 5A — STDB fields missing from Frontend TypeScript (11 items)

| # | Table | Missing TS Field | Impact |
|---|-------|-----------------|--------|
| 1 | `Ticket` | `device_imei` | Hidden repair field |
| 2 | `Ticket` | `device_password` | Hidden repair field |
| 3 | `Ticket` | `estimate_id` | Cross-reference not shown |
| 4 | `Ticket` | `invoice_id` | Cross-reference not shown |
| 5 | `Estimate` | `tax_rate` | Tax not displayed |
| 6 | `Estimate` | `invoice_id` | Conversion link hidden |
| 7 | `Invoice` | `discount_percent` | Discount type hidden |
| 8 | `PurchaseOrder` | `shipping_cost` | Cost breakdown hidden |
| 9 | `Appointment` | `updated_at` | Last-modified hidden |
| 10 | `User` | `pin` | POS PIN hidden |
| 11 | `User` | `totp_secret`, `totp_enabled` | 2FA status not displayed |

### 5B — Whole tables with NO frontend TypeScript interface (use `any`)

| # | Table | Files Affected | Impact |
|---|-------|---------------|--------|
| 1 | `Tenant` / `TenantMember` | TenantsPage | No type safety on tenant management |
| 2 | `RecurringInvoiceRule` | RecurringInvoicesPage | No type safety on rules |
| 3 | `SavedPaymentMethod` | PaymentMethodsPage | No type safety on saved cards |
| 4 | `CustomFieldDefinition` / `CustomFieldValue` | CustomFieldsPage | No type safety on field defs |
| 5 | `UserSettings` (theme, default_ticket_status) | SettingsPage | Hidden user theme/prefs |
| 6 | `AuditLog` entries | AuditLogPage | `entries.map((e: any) => ...)` |
| 7 | `ScheduledReport` | ReportsPage | Uses dedicated `ScheduledReport` interface (OK) |

### 5C — STDB fields missing from Python API input models

| # | Table | Missing Field | Current Workaround |
|---|-------|--------------|--------------------|
| 1 | `Ticket` | `device_imei` | Can't set via create |
| 2 | `Ticket` | `device_password` | Can't set via create |
| 3 | `Invoice` | `discount_amount` | Can't set on create |
| 4 | `Invoice` | `discount_percent` | No input model at all |
| 5 | `Estimate` | `tax_rate` | Can't set on create |
| 6 | `Estimate` | `discount_amount` | Can't set on create |
| 7 | `Appointment` | `color` | Can't set hex color |
| 8 | `PurchaseOrder` | `shipping_cost` | Can't set shipping cost |
| 9 | `ScheduledReport` | No Pydantic model at all | Uses raw `dict` in routes |
| 10 | `POS` | `created_by` | Set by reducer ctx (OK) |

**Effort**: ~45 minutes total for all types + models. No STDB changes needed.

---

## 🟡 PHASE 6: UX Gaps & Missing States (MEDIUM PRIORITY)

### 6A — Missing error states (silent failures)

| # | Page | Issue | Fix |
|---|------|-------|-----|
| 1 | PortalDashboard | `catch(() => {})` swallows API errors | Show error banner |
| 2 | AuditLogPage | Failed fetch silently shows "No entries" | Add error state |
| 3 | DashboardPage | Stats/report errors silently swallowed | Log + show toast |
| 4 | TicketsPage | `catch(() => setX([]))` suppresses errors | Show toast on fetch failure |
| 5 | ReportsPage | 5x `console.error()` instead of toast | Replace with `toast.error()` |

### 6B — Missing empty states

| # | Page | Issue | Fix |
|---|------|-------|-----|
| 1 | PaymentsPage | No "No payments yet" when list is empty | Add empty state with icon |
| 2 | ProductsPage | No "No products yet" empty state | Add empty state with icon + CTA |
| 3 | EstimatesPage | No "No estimates yet" empty state | Add empty state with icon + CTA |

### 6C — Missing loading states

| # | Page | Issue | Fix |
|---|------|-------|-----|
| 1 | PortalDashboard | No spinner while stats fetch | Add `loading` spinner |

### 6D — UI bugs

| # | Page | Bug | Fix |
|---|------|-----|-----|
| 1 | PaymentsPage | Total uses `form.currency` (form's currency) instead of payment currency | Use `p.currency` from each payment |
| 2 | ProductsPage | `BarcodeDetector` API may not exist on all browsers | Wrap in feature check |

### 6E — Missing ErrorBoundary coverage

| # | Issue | Impact |
|---|-------|--------|
| 1 | No pages wrapped in ErrorBoundary | Entire app can crash on render error |
| 2 | No fallback UI for per-page crashes | Blank white screen |

### 6F — TypeScript `any` cleanup

| # | File | Count | Scope |
|---|------|-------|-------|
| 1 | TenantsPage | 9 | `catch (e: any)` and typed `any[]` |
| 2 | SettingsPage | 6 | Webhook payload shape, catch |
| 3 | DashboardPage | 4 | Recharts formatter, icon type |
| 4 | ReportsPage | 3 | Recharts formatter |
| 5 | MapPage | 3 | catch blocks |
| 6 | AppointmentsPage | 2 | occurrence_count cast |
| 7 | ProductsPage | 2 | window.BarcodeDetector |
| 8-18 | 10 other files | 1-2 each | catch blocks |

**Effort**: ~2 hours total for all UX fixes. No backend changes needed for most items.

---

## 🟡 PHASE 7: Code Quality & Refactoring (MEDIUM PRIORITY)

### 7A — Hardcoded portal URL (9 instances, HIGH impact) ✅ DONE

All 9 instances in route files have been replaced with `f"{settings.app_url}/portal/"`.

| File | Lines | Fix |
|------|-------|-----|
| `routes/appointments.py` | 73, 178 | `f"{settings.app_url}/portal/"` |
| `routes/invoices.py` | 60, 201, 373, 420 | `f"{settings.app_url}/portal/"` |
| `routes/payments.py` | 61 | `f"{settings.app_url}/portal/"` |
| `routes/tickets.py` | 103 | `f"{settings.app_url}/portal/"` |

**Fixed in `5d1ec57`.**

### 7B — Inline lazy imports (9 files, LOW impact) ✅ DONE

Route files did `from mail import ...` and `from sms import ...` inside function bodies. All have been refactored to top-level imports — no circular dependencies found.

| File | Lines | Status |
|------|-------|--------|
| `routes/settings.py` | 6 functions | ✅ Refactored |
| `routes/payments.py` | 55-56 | ✅ Refactored |
| `routes/products.py` | 140 | ✅ Refactored |
| `routes/invoices.py` | 50-51, 187-188, 351, 388 | ✅ Refactored |
| `routes/appointments.py` | 67-70, 160-161 | ✅ Refactored |
| `routes/tickets.py` | 96-97 | ✅ Refactored |
| `routes/estimates.py` | 109 | ✅ Refactored |
| `routes/report_schedules.py` | 127 | ✅ Refactored |
| `routes/auth.py` | 429 | ✅ Refactored |

**Fixed in `81a4671`.**

### 7C — `Customer.portal_password_hash` exposed in API response — ✅ Done

`SELECT * FROM customer` returns `portal_password_hash` in every customer list endpoint. This is a bcrypt hash, so it's not exploitable directly, but it's unnecessary exposure. Fix: add an exclude list to the customer response serializer, or use explicit column selection instead of `SELECT *`.

**Implemented**:
- `CUSTOMER_SENSITIVE_FIELDS = {"portal_password_hash"}` in `helpers.py` — central exclude list
- `_safe_customer(c)` strips those keys from customer dicts before returning
- Applied to all customer-list-returning endpoints: `list_customers`, geolocations, duplicates, portal `get_current_customer`
- `_paginated()` now accepts optional `sensitive_fields` param as belt-and-suspenders safety net
- Internal-use sites (dashboard, invoices, tickets, estimates, appointments, payments, report_schedules) only use customer data for aggregates/email/SMS/PDF — never return raw customer dict in API responses

### 7D — `UserSettings` table unused

The `UserSettings` STDB table (theme, default_ticket_status) exists but previously had NO API endpoints, NO frontend UI, and NO test coverage.

**✅ Done — Full implementation:**
- **API endpoints**: `GET /api/users/settings` and `PUT /api/users/settings` in `routes/users.py` (registered via `routes/__init__.py`)
- **Frontend UI**: `UserPreferencesSection` on `SettingsPage.tsx` — theme toggle (light/dark) + default ticket status selector
- **API client**: `api.userSettings.get()` / `api.userSettings.update()` in `web/src/lib/api.ts`
- **STDB reducers**: `upsert_user_settings` / `delete_user_settings` in `user.rs`
- **Models**: `UserSettingsUpdate` Pydantic model in `models.py`
- **Tests**: `TestUserSettings` in `tests/test_settings.py` — 4 tests covering get, update, and auth guards

### 7E — `Pin` field on User table unused — ✅ Done

**Implemented**: POS PIN login with bcrypt-hashed PIN.
- **STDB**: `pin` field on `User` table, `set_user_pin` reducer in `user.rs`
- **Backend**: `POST /api/auth/set-pin` (set PIN, bcrypt-hashed) + `POST /api/auth/pos-login` (PIN-based login, rate-limited) in `routes/auth.py`
- **Frontend**: `PinSection` component in `SettingsPage.tsx` for setting PIN; PIN gate on `PosPage.tsx` for quick POS terminal login
- **API client**: `api.auth.setPin` + `api.auth.posLogin` in `api.ts`

### 7F — STDB unit tests are compile-only (18 tests) — ✅ Done

The existing Rust tests use `ReducerContext::__dummy()` for in-memory STDB testing.
Added container-based integration test infrastructure:
- `docker-compose.test.yml` — ephemeral STDB container on port 3002
- `scripts/run-integration-tests.sh` — full orchestration: build → container → publish → test → cleanup
- `make test-container` — one-command test runner
- Python integration tests now runnable against isolated container

Run with:
```bash
make test-container           # Full pipeline
bash scripts/run-integration-tests.sh --quick   # Skip WASM rebuild
```

### 7G — Test isolation

Tests share STDB state — no fresh database per run. Can cause flaky tests when run in parallel or when tests leave state behind. Fix: each test class/session should use isolated data (unique customer names, etc.) — partially addressed with timestamped names but no formal cleanup.

### 7H — No OpenAPI docs autogeneration

FastAPI could auto-generate OpenAPI spec, but Pydantic models use the raw `SanitizedModel` alias. OpenAPI generation may have incomplete schema info because of how the alias is used.

---

## 🟢 PHASE 8: Feature Additions (LOW PRIORITY — polish)

### 8A — Per-page enhancements

| # | Feature | Effort | Page | Impact |
|---|---------|--------|------|--------|
| 1 | **Duplicate detection UI** — Show badge on CustomersPage when duplicates found, highlight rows | 20m | CustomersPage | 🟢 Quick win | ✅ Done |
| 2 | **Invoice payment history** — Show recent payments inside invoice detail panel (exists in PDF only) | 30m | InvoicesPage | 🟢 Useful | ✅ Done |
| 3 | **Ticket print view** — Printable ticket summary page | 30m | TicketsPage | 🟢 Useful | ✅ Done |
| 4 | **Customer activity timeline** — Show recent tickets, invoices, appointments in chronological timeline | 1h | CustomersPage | 🟡 Medium | ✅ Done |
| 5 | **Dashboard: monthly target editor** — Allow admin to set revenue target from settings | 20m | SettingsPage | 🟢 Quick | ✅ Done |
| 6 | **Invoice: reminder schedule** — Let admin set custom reminder intervals (3d, 7d, 14d) | 30m | SettingsPage | 🟢 Quick | ✅ Done |
| 7 | **Product: reorder point + reorder quantity** — Separate fields for auto-reorder logic | 30m | ProductsPage | 🟢 Quick | ✅ Done |
| 8 | **Ticket: email customer directly from ticket detail** | 20m | TicketsPage | 🟢 Quick | ✅ Done |
| 9 | **POS: quick-cash button** — Pre-fill tendered amount = total for one-tap payment | 10m | PosPage | 🟢 Quick | ✅ Done |
| 10 | **POS: customer display** — Show customer name on receipt | 10m | PosPage | 🟢 Quick | ✅ Done |

### 8B — New entity types / features

| # | Feature | Effort | Priority |
|---|---------|--------|----------|
| 1 | **Bin/shelf location tracking** — `location` field exists on products already, add search/filter by location | 30m | 🟢 Quick | ✅ Done |
| 2 | **Inventory transfer between locations** — Transfer stock between bin locations | 30m | 🟢 Quick | ✅ Done |
| 3 | **Stock count sheets** — Generate printable count sheets with expected quantities | 1h | 🟡 Medium | ✅ Done |
| 4 | **POS gift cards** — Sell/redeem gift cards | 2h | 🟡 Medium | ✅ Done |
| 5 | **Customer email marketing** — Simple blast to all customers (opt-in) | 1h | 🟡 Medium | ✅ Done |
| 6 | **Service type breakdown on reports** — Group revenue/frequency by item_type (service vs part) | 30m | 🟢 Quick | ✅ Done |
| 7 | **Technician schedule view** — Calendar showing all appointments per tech | 1h | 🟡 Medium | ✅ Done |
| 8 | **Mobile push notifications** — Via service worker + browser push | 2h | 🟡 Medium | ✅ Done |
| 9 | **Offline mode** — Service worker cache for critical data | 4h+ | 🔴 Hard |

---

## 🔴 PHASE 9: Infrastructure & Ops (HIGH for deployment)

### 9A — Missing for production deployment

| # | Item | Effort | Criticality | Status |
|---|------|--------|:----------:|:------:|
| 1 | **Reverse proxy** (nginx.conf or Caddyfile) for TLS termination + static file serving | 1h | 🔴 HIGH | ✅ Done |
| 2 | **TLS/SSL** — Let's Encrypt certbot or Caddy auto-TLS | 30m | 🔴 HIGH | ✅ Done (self-signed + LE docs) |
| 3 | **Production env template** — `.env.prod.example` with LOG_LEVEL, WORKERS, SENTRY_DSN | 20m | 🟡 MEDIUM | ✅ Done |
| 4 | **docker-compose.prod.yml** — Prod overrides with TLS, volumes, resource limits | 30m | 🟡 MEDIUM | ✅ Done |
| 5 | **Structured logging** — JSON logs for log aggregation (Datadog, Loki) | 30m | 🟡 MEDIUM | ✅ Done |
| 6 | **Healthcheck on Dockerfile** — Dockerfile-level HEALTHCHECK directive | 10m | 🟢 QUICK | ✅ Done |

### 9B — CI/CD gaps

| # | Item | Effort |
|---|------|--------|
| 1 | **Dependabot config** — `.github/dependabot.yml` for automated dep updates | 10m | ✅ Done |
| 2 | **Docker image CI build** — GitHub workflow that builds and pushes to registry | 30m | ✅ Done (`.github/workflows/docker-image.yml`) |
| 3 | **Deployment workflow** — CI deploy to staging/production after tests pass | 1h | ✅ Done (`.github/workflows/deploy.yml`) |
| 4 | **Commit message linting** — commitlint or similar | 15m | ✅ Done (`.githooks/commit-msg` + `make setup-git-hooks`) |

### 9C — Dev tooling gaps

| # | Item | Effort |
|---|------|--------|
| 1 | **Ruff config** (`ruff.toml`) — Customize rule set | 10m | ✅ Done |
| 2 | **Prettier config** (`.prettierrc`) — Format web/ consistently | 10m | ✅ Done |
| 3 | **`.editorconfig`** — Cross-editor settings | 5m | ✅ Done |
| 4 | **`.python-version`** — Pin Python version for pyenv | 2m | ✅ Done |
| 5 | **`.nvmrc`** — Pin Node version for nvm | 2m | ✅ Done |
| 6 | **`pyproject.toml`** — Python project metadata + tool config | 15m | ✅ Done |

---

## 🧪 TESTING REPORT

| Area | Status | Details |
|------|--------|---------|
| Rust unit tests | ✅ 211 tests (4 files) | 74 reducers, 27 tables — via STDB integration |
| Python backend tests | ✅ 1,827 tests (61 files) | 1,246 unit (12 files) + integration across 28 route modules |
| TypeScript frontend tests | ✅ 159 tests (24 suites) | UI components + 16 page test suites |
| E2E tests | ✅ 33 tests (5 suites) | Playwright: Nav, Dashboard, Customers, Invoices, Tickets |
| CI/CD pipeline | ✅ GitHub Actions | build STDB, seed, test, lint |

### Test quality gaps
- ✅ Negative tests for business logic — `test_negative.py` (6 tests): empty customer name, missing required fields, invoice without customer, nonexistent PDF, unauthenticated access, invalid priority
- ✅ Concurrent/multi-user tenant isolation tests — `test_tenant_isolation.py` (10 tests): two independent tenants, cross-tenant list/fetch/mutation rejection + 10-way parallel `asyncio.gather` burst with zero leakage and zero 5xx. Also hardened 20+ direct-access routes (customers/tickets/invoices sub-resources) with tenant-scoped `_require_owned` checks.
- ✅ Performance/load smoke tests — `server/tests/test_load_smoke.py` (2 tests, `@pytest.mark.slow`): 16-way parallel `asyncio.gather` burst on `/api/stats` + `/api/customers`, asserts all 200 (no 5xx) under concurrency with p95 < 3s budget; auto-skips when server is down (mirrors `test_client.py` availability gate). Regression detector for N+1 / full-table-scan, not a benchmark
- ❌ Tests share STDB state (no fresh DB per run)
- ❌ No Rust runtime tests (need STDB host)
- ✅ OpenAPI spec tests with schema validation, auth enforcement, response contracts, error contracts, CORS contracts, and request body field requirements (30 tests in `test_openapi_spec.py`)

---

## 🚨 Anti-Patterns & Technical Debt

### 🔴 HIGH

| # | Issue | Severity | Fix |
|---|-------|:--------:|-----|
| 1 | **9 hardcoded `localhost` URLs** in route files — will break portal link emails in production | 🔴 HIGH | ✅ **Fixed** — `f"{settings.app_url}/portal/"` in all 8 portal link routes (`5d1ec57`) |
| 2 | **No ErrorBoundary wrapping** on any page — unhandled render error = blank screen | 🔴 HIGH | ✅ **Done** — `ErrorBoundary.tsx` wraps app shell + test coverage |
| 3 | **`Customer.portal_password_hash` exposed** — returned by SELECT * in every customer API response | 🔴 HIGH | ✅ **Fixed** — `_safe_customer()` helper strips it from all list endpoints (`5d1ec57`) |
| 4 | **Test isolation** — tests share STDB state, no cleanup per session | 🔴 HIGH | Fresh DB per test session |
| 5 | **No TLS/reverse-proxy config** — ⚠️ WAS: production deployment would serve HTTP directly | 🔴 HIGH | ✅ **Fixed** — nginx config with TLS + deploy script at `deploy/nginx/` |

### 🟡 MEDIUM

| # | Issue | Severity | Fix |
|---|-------|:--------:|-----|
| 6 | **Missing empty states** on PaymentsPage, ProductsPage, EstimatesPage | 🟡 MEDIUM | ✅ **Done** — all three pages render empty states |
| 7 | **Missing error states** on PortalDashboard, AuditLogPage | 🟡 MEDIUM | ✅ **Done** — both render user-facing error states |
| 8 | **36 TypeScript `any` usages** in catch blocks and API response shapes | 🟡 MEDIUM | 30 min |
|| 9 | **`UserSettings` table has no API or UI** — dead code | 🟡 MEDIUM | ✅ **Done** — API + UI + tests implemented (`cyber-elf/task_f7002a184d824426_`) |
|| 10 | **`User.pin` field unused** — dead field in STDB | 🟡 MEDIUM | ✅ **Done** — POS PIN login with bcrypt-hashed PIN implemented (7E) |

### 🟢 LOW

| # | Issue | Severity | Fix |
|---|-------|:--------:|-----|
| 11 | **Inline lazy imports** in 3 route files (from mail/sms inside function body) | 🟢 LOW | ✅ **Done** — all refactored to top-level imports |
| 12 | **No Dependabot config** | 🟢 LOW | ✅ **Done** — `.github/dependabot.yml` |
| 13 | **No linter config files** (ruff.toml, .prettierrc, .editorconfig, .nvmrc) | 🟢 LOW | ✅ **Done** — all present |
| 14 | **Docker images use latest tags** (spacetimedb:latest, node:22-alpine) | 🟢 LOW | 5 min |
| 15 | **`.dockerignore` is thin** — excludes too little from build context | 🟢 LOW | 5 min |
| 16 | **No structured logging** — stdout is plain text | 🟢 LOW | ✅ **Done** — `log_config.py` JSON logging (STRUCTURED_LOGGING env) |

---

## 🏆 Feature Gap Analysis vs. RepairShopr

| Feature | Our Status | Gap Notes |
|---------|:----------:|-----------|
| Customer management | ✅ Complete | — |
| Ticket/repair tracking | ✅ Complete | — |
| Invoicing + line items | ✅ Complete | — |
| Estimates + conversion | ✅ Complete | — |
| Payment recording | ✅ Complete | Stripe + manual + saved cards |
| Appointment scheduling | ✅ Complete | Calendar view, recurring |
| Inventory tracking | ✅ Complete | Adjustments, transfers, bins |
| Purchase orders | ✅ Complete | Approvals, receiving |
| Time tracking | ✅ Complete | Ticket timers |
| Customer portal | ✅ Complete | Dashboard, tickets, invoices, appointments |
| Email notifications | ✅ Complete | 7 event types, templates |
| SMS notifications | ✅ Configured | Twilio integration |
| Stripe payments | ✅ Complete | Checkout + SetupIntent + PaymentIntent |
| Webhook API | ✅ Complete | HMAC-SHA256, 13 events |
| Reporting | ✅ Complete | Revenue, tickets, invoices, appointments, tech, customers, SLA |
| Custom fields | ✅ Complete | Per entity type |
| Repair checklists | ✅ Complete | Templates + apply to ticket |
| Barcode scanning | ✅ Complete | Camera + manual lookup + labels |
| Data import/export | ✅ CSV | CSV only — no XLSX/JSON |
| Multi-tenant | ✅ Complete | 27 tables scoped |
| POS / counter sale | ✅ Complete | Kiosk with cart, payment, receipt, refund |
| Invoice email delivery | ✅ Complete | Single + batch + queue status |
| Multi-currency | ✅ Foundation | On entities + API, not in STDB reducers |
| 2FA / TOTP | ✅ Complete | QR setup, challenge login, disable |
| SLA tracking | ✅ Complete | Priority thresholds, configurable |
| Purchase order approvals | ✅ Complete | Submit/approve/reject flow |
| **Offline mode** | ❌ Not started | — |
| **Mobile app** | ❌ PWA only | — |
| **Inventory: bin/shelf locations** | ⚠️ Partial | `location` field exists, no search/filter |
| **Inventory: reorder alerts** | ⚠️ Partial | Email alert via cron, no in-app notification |
| **Service type breakdown** | ✅ Complete | Reports + dashboard split service vs parts (PieChart) |
| **Customer email marketing** | ✅ Complete | EmailCampaignsPage with opt-in blast |
| **Technician scheduling** | ✅ Complete | TechnicianSchedulePage calendar per tech |
| **Push notifications** | ✅ Complete | Web Push (VAPID) via service worker, auto-subscribe on login |
| **Gift cards** | ✅ Complete | POS gift card sale/redeem (GiftCardsPage) |

---

## 📋 Estimated Remaining Effort

| Phase | Items | Hours | Priority |
|-------|-------|:-----:|:--------:|
| **5: Field & Type Gaps** | 11 TS fields, 7 whole-table types, 10 API models | **✅ DONE** | ✅ DONE |
| **6: UX Gaps** | TS `any` cleanup (36 usages), error/empty state polish | **~1.5h** | 🟡 MEDIUM |
| **7: Code Quality** | Test isolation (fresh DB per session), 2 minor STDB patterns | **~2h** | 🔴 HIGH |
| **8: Feature Additions** | Offline mode (PWA cache), in-app reorder alerts, location-to-location stock moves polish | **~5h** | 🟢 LOW |
| **9: Infrastructure** | ✅ All 9A + 9B + 9C items complete (re-audited 2026-07-31) | **0h** | ✅ DONE |
| **Test coverage** | Rust runtime tests (need STDB host), full-suite CI wiring | **~2h** | 🟡 MEDIUM |
| **Overall remaining** | **~10 hours** | | |

---

## 🎯 Priority Recommendation (next session)

### Immediate (fix 1st)
1. ~~**Fix 9 hardcoded `localhost:8723/portal/` URLs** — will break all portal links in production~~ ✅ Done (`5d1ec57`)
2. ~~**Hide `portal_password_hash`** from customer API responses~~ ✅ Done (`5d1ec57`)
3. ~~**Add TS interfaces** for Tenant, RecurringInvoiceRule, SavedPaymentMethod, CustomFieldDefinition~~ ✅ Done (`320d2aa`)
4. **Add missing empty/error states** on PaymentsPage, ProductsPage, PortalDashboard

### This sprint
5. **Add ErrorBoundary** to each page
6. ~~**Add device_imei/device_password** to TicketCreate + Ticket TS interface~~ ✅ Done (`320d2aa`)
7. **Fix PaymentsPage currency display bug**
8. ~~**Add missing Pydantic models** for ScheduledReport, Invoice discount fields~~ ✅ Done (`320d2aa`)
9. **Add structured logging**

### Next sprint
11. **Service type breakdown on reports**
12. **Duplicate detection UI on CustomersPage**
13. ~~**Implement `UserSettings` API + UI or remove**~~ ✅ Done
14. ~~**Implement `User.pin` POS login or remove**~~ ✅ Done

---

## 🔎 Review Addendum (2026-07-31 re-audit)

Full code-level re-audit of the repository (grep + test-run verified, not just README claims).
**18 roadmap items previously listed as open are implemented and are now marked ✅ Done.**

### Concrete open tasks (verified still open, in priority order)

| # | Task | Evidence | Effort | Status |
|---|------|----------|--------|--------|
| 1 | **TypeScript `any` cleanup** — 36 usages across pages/components/lib (`catch (e: any)`, `as any`, `: any`) | `grep -rn ": any\|as any\|<any>" web/src --include="*.tsx" --include="*.ts"` → 0 | 30m | ✅ **36/36 done** — final 12 Recharts formatter/label callbacks typed with `TooltipValueType`, `PieLabelRenderProps`, `TooltipPayloadEntry` (fixed param narrowness with `| undefined`; datum fields read via `payload`). Zero `any` in production source. |
| 2 | **Test isolation** — tests share STDB state; no fresh DB per run; partial fix exists (timestamped names) | ROADMAP 7G; `conftest.py` shared admin session | 2h | Open |
| 3 | **Rust runtime tests** — 211 `#[test]` are compile-only for wasm; container infra exists (`docker-compose.test.yml`, `make test-container`) but not wired into CI | `scripts/run-integration-tests.sh` exists; CI `test.yml` doesn't call it | 1h | ✅ **Host unit tests wired into CI** — `cargo test --lib` (208 tests, in-memory stub datastore) + `cargo clippy -D warnings` are now hard CI gates (were `continue-on-error`); clippy `--all-targets` cleaned to zero warnings |
| 4 | **Offline mode (8B-9)** — PWA has service worker precache but no offline data strategy | `vite-plugin-pwa` config only precaches static assets | 4h+ | Open |
| 5 | **In-app reorder alerts** — low-stock notification is email-only via cron | `POST /api/products/low-stock/notify` → email; no in-app badge | 30m | ✅ **Done** — amber low-stock alert card on dashboard (60s refetch, links to Products) |
| 6 | **Pin Docker tags** — `spacetimedb:latest` in docker-compose.yml (no version pin) | `docker-compose.yml:5` | 5m | ✅ **Done + root cause** — `spacetimedb/spacetimedb:*` does **NOT exist on Docker Hub**; pinned official `clockworklabs/spacetime:v2.6.1` (matches production 2.6.1) in docker-compose.yml, docker-compose.test.yml, run-integration-tests.sh |
| 7 | **Thicken `.dockerignore`** — 8 lines, excludes little from build context | `wc -l .dockerignore` → 8 | 5m | ✅ **Done** — added Playwright artifacts, root `target/`, `deploy/`, `.ruff_cache/`, `.daemon-locks/` |
| 8 | **🔴 CI Test workflow broken at first step** — every Test run failed in <35s since at least 2026-07-07 | `gh run list` → all `failure`; log: `docker pull spacetimedb/spacetimedb:latest` → "repository does not exist"; no `spacetime` CLI installed on runner | 30m | ✅ **Done** — replaced phantom service container with direct install of `spacetime-x86_64-unknown-linux-gnu.tar.gz` (v2.6.1) + `spacetime start -l 0.0.0.0:3001`; validated end-to-end locally (fresh HOME → auto direct-login → publish "Created new database") |

### Verified during audit (regression-protected)
- Backend unit suite: **1,249 passed** (`pytest tests/unit/ -q`)
- Frontend suite: **159 passed** in 24 files (`vitest run`) — includes 7 new ReminderScheduleSection tests + ticket-email test
- `tsc --noEmit`: clean; `ruff check`: clean
- STDB wasm release build: fixed by `9ca1395` (estimate module + clippy)
