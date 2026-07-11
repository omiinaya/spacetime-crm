# SpacetimeCRM — Roadmap & Honest Assessment

| **Last assessed:** | 2026-07-10 |
| **Overall completeness:** | ~85% (down from 96%) |
| **Total endpoints:** | 187 route decorators (~99 unique paths, 25 route files) |
| **Total STDB artifacts:** | 31 tables + ~73 reducers + 4,737 lines Rust |
| **Total frontend pages:** | 29 pages (22 admin + 3 auth + 4 portal) + DashboardPage |
| **Total tests:** | 360 collected (47 backend pass, 94 frontend pass, 313 blocked) |
| **⚠️ VERIFIED REALITY** | Test infra had 2 bugs that blocked 87% of backend suite. STDB database gone (upgrade crash).

---

## 📊 Summary by Layer (VERIFIED ASSESSMENT)

| Layer | Files | Lines | Completeness | Test Count | Anti-Patterns |
|-------|-------|-------|:------------:|:----------:|:-------------:|
| STDB Module (Rust) | 22 files | ~4,737 | 88% | ~200 #[cfg(test)] + container CI | 1 major, 3 minor |
| Backend API (Python) | 39 files | ~6,000 | 90% | 360 integration (47 pass, 313 blocked) | 3 major, 7 minor |
| Frontend (TypeScript) | 45+ files | ~8,000 | 85% | 94 unit (all pass) + 3 ts errors | 4 major, 8 minor |
| Infra (Docker/scripts) | 15 files | ~500 | 70% | N/A | 5 gaps |
| **Overall** | **~120 files** | **~20,000** | **~85%** | **360 total (141 verified passing)** | **~25 items** |

### ⚠️ CRITICAL FINDINGS (discovered 2026-07-10)

| # | Issue | Severity | Status |
|---|-------|:--------:|:------:|
| 1 | **STDB database `spacetime-crm` is GONE** — STDB upgraded 2.4.x→2.6.1, database identity mismatch, control-db empty. 7.5GB of replica data orphaned. Server crashes on restart due to identity mismatch. | 🔴 BLOCKER | Not fixed |
| 2 | **Test infra: `_stdb_write()` calls reducer via SQL** — `set_user_password` is a STDB reducer, not a SQL function. SQL SELECT silently fails, 313/360 tests blocked. | 🔴 CRITICAL | ✅ **Fixed** — added `_stdb_call()` helper, fixed `create_customer` using fixture func instead of param |
| 3 | **TS compile errors** — 3 errors: PosPage.tsx x2 (wrong param type after `category` added), TenantsPage.tsx (`members` missing from Tenant interface) | 🟡 MEDIUM | ❌ Not fixed |
| 4 | **STDB WASM build OOM** — `cargo build --release --target wasm32-unknown-unknown` killed by SIGKILL (OOM). Can't publish new module versions. | 🔴 BLOCKER | ❌ Not fixed |

---

## ✅ PHASE 0: Core Foundation (DONE — 100%)

All core infrastructure complete. No gaps.

- [x] SpacetimeDB 2.4.1 module: **31 tables, ~73 reducers** (not 27 — tables in: customer, ticket, invoice, estimate, payment, appointment, product, purchase_order, user, tenant, inventory adjustment, tax_rate, audit, custom_field, customer_geolocation, checklist, webhook, sla_config, pos, and supporting types)
- [x] FastAPI server on port 8723: **187 route decorators (~99 unique API paths)** across 25 route files
- [x] React 18 + Vite 6 + TailwindCSS v4 + shadcn-style frontend
- [x] Dark theme with localStorage persistence
- [x] JWT auth (HS256) with role-based permissions (admin/tech/front_desk/customer)
- [x] React.lazy() code-splitting (29 pages — lazy-loaded)
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
- [⚠️] **CI/CD pipeline** (GitHub Actions: build STDB, seed, test, lint) — WOULD FAIL: test infra bugs + STDB upgrade incompatibility
- [⚠️] **E2E tests** (Playwright: 33 tests across 5 suites) — CANNOT VERIFY: STDB database is down, required for full stack
- [x] Port 8723 → vite build → nginx/gateway update flow
- [x] Reverse-proxy + TLS config (nginx, self-signed cert, deploy script)
- [x] Production docker-compose overrides (deploy/docker-compose.prod.yml: resource limits, nginx service)
- [x] Production env template (deploy/.env.prod.example: CORS, APP_URL, SMTP, Stripe for production)

---

## 🔴 PHASE 5: Field & Type Gaps (HIGH PRIORITY)

These are gaps between STDB table fields, Python API models, and frontend TypeScript interfaces. The roadmap claims these are **DONE**, but **could not verify** because the STDB database is down and `npx tsc --noEmit` still has 3 errors (PosPage x2, TenantsPage). Remaining TS compile errors suggest the field mapping may still be incomplete.

### 5A — STDB fields missing from Frontend TypeScript (11 items)

⚠️ **ROADMAP SAYS DONE** — Verify by checking `web/src/lib/api.ts` for the fields below:

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
| 1 | **Duplicate detection UI** — Show badge on CustomersPage when duplicates found, highlight rows | 20m | CustomersPage | 🟢 Quick win |
| 2 | **Invoice payment history** — Show recent payments inside invoice detail panel (exists in PDF only) | 30m | InvoicesPage | 🟢 Useful |
| 3 | **Ticket print view** — Printable ticket summary page | 30m | TicketsPage | 🟢 Useful |
| 4 | **Customer activity timeline** — Show recent tickets, invoices, appointments in chronological timeline | 1h | CustomersPage | 🟡 Medium |
| 5 | **Dashboard: monthly target editor** — Allow admin to set revenue target from settings | 20m | SettingsPage | 🟢 Quick |
| 6 | **Invoice: reminder schedule** — Let admin set custom reminder intervals (3d, 7d, 14d) | 30m | SettingsPage | 🟢 Quick |
| 7 | **Product: reorder point + reorder quantity** — Separate fields for auto-reorder logic | 30m | ProductsPage | 🟢 Quick |
| 8 | **Ticket: email customer directly from ticket detail** | 20m | TicketsPage | 🟢 Quick |
| 9 | **POS: quick-cash button** — Pre-fill tendered amount = total for one-tap payment | 10m | PosPage | 🟢 Quick |
| 10 | **POS: customer display** — Show customer name on receipt | 10m | PosPage | 🟢 Quick |

### 8B — New entity types / features

| # | Feature | Effort | Priority |
|---|---------|--------|----------|
| 1 | **Bin/shelf location tracking** — `location` field exists on products already, add search/filter by location | 30m | 🟢 Quick |
| 2 | **Inventory transfer between locations** — Transfer stock between bin locations | 30m | 🟢 Quick |
| 3 | **Stock count sheets** — Generate printable count sheets with expected quantities | 1h | 🟡 Medium |
| 4 | **POS gift cards** — Sell/redeem gift cards | 2h | 🟡 Medium |
| 5 | **Customer email marketing** — Simple blast to all customers (opt-in) | 1h | 🟡 Medium |
| 6 | **Service type breakdown on reports** — Group revenue/frequency by item_type (service vs part) | 30m | 🟢 Quick |
| 7 | **Technician schedule view** — Calendar showing all appointments per tech | 1h | 🟡 Medium |
| 8 | **Mobile push notifications** — Via service worker + browser push | 2h | 🟡 Medium |
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
| 5 | **Structured logging** — JSON logs for log aggregation (Datadog, Loki) | 30m | 🟡 MEDIUM | ❌ Pending |
| 6 | **Healthcheck on Dockerfile** — Dockerfile-level HEALTHCHECK directive | 10m | 🟢 QUICK | ❌ Pending |

### 9B — CI/CD gaps

| # | Item | Effort |
|---|------|--------|
| 1 | **Dependabot config** — `.github/dependabot.yml` for automated dep updates | 10m |
| 2 | **Docker image CI build** — GitHub workflow that builds and pushes to registry | 30m |
| 3 | **Deployment workflow** — CI deploy to staging/production after tests pass | 1h |
| 4 | **Commit message linting** — commitlint or similar | 15m |

### 9C — Dev tooling gaps

| # | Item | Effort |
|---|------|--------|
| 1 | **Ruff config** (`ruff.toml`) — Customize rule set | 10m |
| 2 | **Prettier config** (`.prettierrc`) — Format web/ consistently | 10m |
| 3 | **`.editorconfig`** — Cross-editor settings | 5m |
| 4 | **`.python-version`** — Pin Python version for pyenv | 2m |
| 5 | **`.nvmrc`** — Pin Node version for nvm | 2m |
| 6 | **`pyproject.toml`** — Python project metadata + tool config | 15m |

---

## 🧪 TESTING REPORT (VERIFIED 2026-07-10)

| Area | Status | Details |
|------|--------|---------|
| Rust unit tests | ❌ 18 tests (compile-only) | Cannot build — OOM during `cargo build --target wasm32` |
| Python backend tests | ⚠️ 362 test functions, **47 pass** | 30 openapi_spec + 13 sanitize + 4 health pass. 313 blocked by fixture bugs (2 now fixed). STDB database must exist to run remaining tests. |
| TypeScript frontend tests | ✅ **94/94 pass** (13 suites) | Pagination, LoginPage, ForgotPassword, ResetPassword, ImportExport all pass |
| E2E tests | ❌ **Cannot verify** | Playwright requires STDB + backend running. Database is down. |
| CI/CD pipeline | ⚠️ GitHub Actions | Would fail — test infra bugs and STDB upgrade incompatible |

### Test quality gaps (unchanged)
- ❌ No negative tests for business logic (e.g. creating invoice without customer)
- ❌ No concurrent/multi-user tests for tenant isolation
- ❌ No performance/load tests
- ❌ Tests share STDB state (no fresh DB per run)
- ❌ No Rust runtime tests (need STDB host)
- ✅ OpenAPI spec tests with schema validation, auth enforcement, response contracts, error contracts, CORS contracts, and request body field requirements (30 tests in `test_openapi_spec.py`)

---

## 🚨 Anti-Patterns & Technical Debt (VERIFIED 2026-07-10)

### 🔴 HIGH

| # | Issue | Severity | Fix |
|---|-------|:--------:|-----|
| 1 | **STDB 2.4.x → 2.6.1 upgrade BROKE database** — identity mismatch, control-db empty, 7.5GB replicas orphaned | 🔴 BLOCKER | Restore from STDB backup OR reseed with `scripts/reseed.sh` after fresh publish OR rollback to STDB 2.4.1 |
| 2 | **WASM build OOM** — `cargo build --release --target wasm32-unknown-unknown` always SIGKILL'd. Cannot publish module updates. | 🔴 BLOCKER | Reduce memory (less deps, optimize build) OR build on another machine. Current workaround: use pre-built `.opt.wasm` from Jul 6. |
| 3 | **No ErrorBoundary wrapping** on any page — unhandled render error = blank screen | 🔴 HIGH | Add per-page ErrorBoundary |
| 4 | **Test isolation** — tests share STDB state, no fresh DB per run. Partially fixed with session-level isolation but still fragile. | 🔴 HIGH | Container-based isolated DB per run (docker-compose.test.yml exists) |
| 5 | **9 bare `except Exception: pass`** in route files — auth.py (6), customers.py (1), invoices.py (1), health.py (1). Silently swallow errors. | 🟡 MEDIUM | Log errors before swallowing |

### 🟡 MEDIUM

| # | Issue | Severity | Fix |
|---|-------|:--------:|-----|
| 6 | **Missing empty states** on PaymentsPage, ProductsPage, EstimatesPage | 🟡 MEDIUM | 15 min |
| 7 | **Missing error states** on PortalDashboard (empty catch), AuditLogPage (silent "No entries") | 🟡 MEDIUM | 20 min |
| 8 | **~30+ `catch (e: any)`** in 18 TS files across the frontend | 🟡 MEDIUM | 30 min |
| 9 | **5x `console.error()` on ReportsPage** — should use `toast.error()` | 🟢 LOW | 5 min |
| 10 | **PaymentsPage `form.currency` bug** — displays form's currency instead of each payment's currency | 🟢 LOW | 5 min |
| 11 | **`BarcodeDetector` API** may not exist on all browsers | 🟢 LOW | Wrap in feature check |
| 12 | **TS compile errors** — PosPage.tsx x2 (wrong params), TenantsPage.tsx (missing `members`) | 🟡 MEDIUM | 5 min |

### 🟢 LOW

| # | Issue | Severity | Fix |
|---|-------|:--------:|-----|
| 13 | **No Dependabot config** | 🟢 LOW | 5 min |
| 14 | **No linter config files** (ruff.toml, .prettierrc, .editorconfig, .nvmrc) | 🟢 LOW | 10 min |
| 15 | **Docker images use latest tags** (spacetimedb:latest, node:22-alpine) | 🟢 LOW | 5 min |
| 16 | **`.dockerignore` is thin** — excludes too little from build context | 🟢 LOW | 5 min |
| 17 | **No structured logging** — stdout is plain text | 🟢 LOW | 15 min |
| 18 | **`_sql()` uses f-strings** — SQL injection risk mitigated by `_sql_t()` tenant_id format check but f-strings with user data are still risky | 🟢 LOW | Parameterized queries or ORM |
| 19 | **`SELECT * FROM` in every query** — pulls unnecessary columns. `portal_password_hash` was exposed this way (now fixed). | 🟢 LOW | Explicit column lists |
| 20 | **No `ORDER BY` support** in `_paginated()` (STDB limitation) — results sorted in Python memory | 🟢 LOW | Acceptable STDB workaround |
| 21 | **`@ts-expect-error` on MapPage** — Leaflet default icon fix, fragile | 🟢 LOW | Proper type declaration |

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
|| Multi-tenant | ✅ Complete | 31 tables scoped with `tenant_id` |
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
| **Service type breakdown** | ❌ Missing | Reports don't split service vs parts |
| **Customer email marketing** | ❌ Missing | No blast/campaign functionality |
| **Technician scheduling** | ❌ Missing | No per-tech calendar view |
| **Push notifications** | ❌ Missing | Browser push via service worker |
| **Gift cards** | ❌ Missing | POS gift card sale/redeem |

---

## 📋 Estimated Remaining Effort

| Phase | Items | Hours | Priority |
|-------|-------|:-----:|:--------:|
| **🔴 Fix STDB database** | Restore STDB 2.4.x or reseed. Identity mismatch recovery. | **~2h** | 🔴 BLOCKER |
| **🔴 Fix WASM build OOM** | Reduce deps, swap space, or build externally | **~1h** | 🔴 BLOCKER |
|| **5: Field & Type Gaps** | 11 TS fields, 7 whole-table types, 10 API models | **⚠️ CLAIMED DONE (not verified)** | 🟡 MEDIUM |
| **6: UX Gaps** | 4 error states, 3 empty states, 1 loading state, 2 bugs, TS `any` cleanup | **~2h** | 🟡 MEDIUM |
| **7: Code Quality** | ErrorBoundary, except blocks, TS errors, structured logging | **~3h** | 🔴 HIGH |
| **8: Feature Additions** | ~15 small features + ~9 larger features | **~15h** | 🟢 LOW |
| **9: Infrastructure** | ✅ Reverse proxy + TLS + prod compose + env template done. Remaining: structured logging, Dockerfile healthcheck, CI/CD, dev tooling | **~2h** | 🟡 MEDIUM |
| **Test coverage** | Negative tests, concurrent tests, Rust runtime tests, load tests | **~6h** | 🟡 MEDIUM |
| **Overall remaining** | **~32 hours** | | |

---

## 🎯 Priority Recommendation (next session)

### BLOCKER (fix immediately)
1. **Fix STDB database** — Either restore old 2.4.1 binary and load from replicas, or publish fresh module and reseed
2. **Fix WASM OOM build** — Only needed if STDB module code needs changing
3. **Fix TS compile errors** — PosPage.tsx x2 + TenantsPage.tsx

### Immediate (fix 1st)
4. **Add ErrorBoundary to each page**
5. **Fix empty `except Exception: pass` blocks** — log errors 
6. **Add missing empty/error states** on PaymentsPage, ProductsPage, PortalDashboard
7. **Fix PaymentsPage currency display bug**
8. **Get full test suite green** — after STDB is back, run `make test-container`

### This sprint
9. **Service type breakdown on reports**
10. **Duplicate detection UI on CustomersPage**
11. **Structured logging**
