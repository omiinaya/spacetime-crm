# SpacetimeCRM — Roadmap & Honest Assessment

| **Last assessed:** 2026-06-30
| Overall completeness: ~92% (+5% since last assessment)

---

## 📊 Summary

| Layer | Lines | Completeness | Test Coverage | Anti-Patterns |
|-------|-------|:------------:|:-------------:|:-------------:|
| STDB Module (Rust) | 1,711 | 86% | 0% (unit) | 3 major, 4 minor |
| Backend API (Python) | ~3,925 | 90% | 22% (API paths) | 3 major, 2 minor |
| Frontend (TypeScript) | 7,469 | 75% | 7% (unit) | 3 major, 3 minor |
| Infra (Docker/scripts) | 45 (Dockerfile) | 85% | N/A | 2 minor |
| **Tests** | **~4,900 (124 tests)** | **Added this sprint** | **N/A** | **3 gaps** |
| **Overall** | **~17,400** | **~89%** | **40%** | **9 items** |

### 🟢 Sprint Wins (since last assessment)

- **React Query — WIRED** — QueryProvider wraps the entire app. CustomersPage converted to useQuery/useMutation (cache invalidation, dedup, stale-while-revalidate). Template for further page conversions.
- **Route splitting — COMPLETED** — main.py 2,390→55 lines, 20 APIRouter modules in routes/ package. All 52 backend tests pass.
- **Frontend code-splitting — COMPLETED** — React.lazy() for all 23 pages, main bundle 980KB→249KB (75% drop)
- **Frontend TypeScript tests — ADDED** — 52 tests across 8 suites
- **E2E tests — ADDED** — 33 Playwright tests across 5 suites
- **CI/CD pipeline — ADDED** — GitHub Actions: build STDB, seed, test, lint
- **Password recovery — ADDED** — forgot-password + reset-password flows
- **Tenant management UI — ADDED** — TenantsPage with create/edit/delete/members
- **Pagination — ADDED** — offset/limit + total on all 15 list endpoints
- **Pydantic validation — ADDED** — all 49 POST/PUT endpoints use typed models (0 remaining body: dict)
- **Rate limiting — ADDED** — slowapi middleware (100/min default, 10/min auth)
- **Input sanitization — ADDED** — HTML strip on all Pydantic models via SanitizedModel
- **Exception handlers — ADDED** — JSON error responses with no stack-trace leak
- **Shared httpx client — ADDED** — single connection pool replaces 9 inline AsyncClient() instances

---

## Phase 1: Foundation ✅✅ (97% complete)

- [x] SpacetimeDB module with 25 tables and 70 reducers
- [x] FastAPI REST server with 91 endpoints
- [x] React dashboard with sidebar navigation and dark theme
- [x] Customers page (list, create, edit, delete, search)
- [x] Tickets page (list, create, status workflow, notes)
- [x] Invoices page (list, create, status, line items)
- [x] Payments page (list, record payments)
- [x] Appointments page (schedule with calendar, status CRUD)
- [x] Products page (inventory tracking, low stock alerts)
- [x] Estimates page (quotes with line items)
- [x] Purchase Orders page (vendor ordering + receiving)
- [x] Users page (staff management)
- [x] Dashboard stats overview
- [x] **Pydantic input validation** — models created, proof-of-concept endpoints converted
- [x] **Frontend code-splitting** — `React.lazy()` for all 23 pages
- [x] **Integration tests** — 39 tests covering auth, customers, tickets, tenants, validation
- [x] **Pagination** — offset/limit + total on all 15 list endpoints
- [x] **Pydantic input validation** — **all 49 endpoints** now use typed models
- [x] **Helpers extraction** — `helpers.py` created, main.py -260 lines
- [x] **Route splitting** — `main.py` 2,390→55 lines, 20 APIRouter modules in `routes/` package, all 39 tests passing

---

## Phase 2: Real-World Features ✅ (80% complete)

- [x] Customer portal (web login for customers to view tickets/invoices)
- [x] Customer map (geographic visualization with Leaflet)
- [x] Email notifications (ticket status, invoice reminders, payment confirmations)
- [x] PDF generation (invoices, estimates, tickets with WeasyPrint)
- [x] Calendar view for appointments
- [x] Time tracking with ticket timers
- [x] Inventory adjustments (add/remove stock with reason)
- [x] Purchase order receiving (receive against PO, auto-update stock)
- [x] Tax rate configuration
- [ ] 📌 **Email templates** — all hardcoded in `mail.py`, no customization
- [ ] 📌 **Recurring appointments** — no repeat/schedule pattern
- [ ] 📌 **Low stock alerts** — threshold exists in DB, no notification triggers

---

## Phase 3: Advanced ⚠️ (65% complete)

- [x] Multi-tenant support (25 tables with `tenant_id`)
- [x] SMS notifications (Twilio — API integration works)
- [x] Stripe payment processing (checkout sessions)
- [x] Reporting dashboard (revenue by period, tech productivity)
- [x] Barcode scanning for products
- [x] Repair checklist templates
- [x] Custom fields per customer/ticket
- [x] Webhook integration (HMAC-SHA256 signed, 13 events)
- [ ] 📌 **Saved customer payment methods** — not implemented
- [ ] 📌 **Portal payment UX** — checkout session creates but UI is basic
- [ ] 📌 **Report scheduling/exports** — no saved reports, no email reports
- [ ] 📌 **Recurring invoices** — no auto-generation or scheduling

---

## Phase 4: Production Readiness ⚠️ (55% complete)

- [x] Authentication (JWT login for staff + customer portal)
- [x] Role-based permissions (admin, tech, front_desk)
- [x] Audit logging (58 calls across all endpoints)
- [x] Data export (CSV)
- [x] Docker Compose for one-command deploy
- [x] Backup/restore scripts (`scripts/publish-stdb.sh`)
- [x] Health checks and monitoring
- [x] **SQL injection fix** — `_sql_t()` validates tenant_id format
- [x] **Input validation** — Pydantic models created, login + customers converted
- [x] **Frontend code-splitting** — 980KB → 249KB main bundle
- [x] **Integration tests** — 39 tests covering auth, CRUD, security, tenant isolation
- [x] **CORS locked** — `allow_origins=[settings.cors_origin]`
- [x] **Pydantic conversion** — 47/49 POST/PUT endpoints converted (only mail/sms settings remain)
- [x] **Exception handlers** — all unhandled errors return JSON, no stack-trace leak
- [x] **Shared httpx client** — single connection pool replaces 9 inline `AsyncClient()` instances
- [x] **Rate limiting** — slowapi middleware: 100/min default, 10/min on auth, 30/min on settings
- [x] **Password recovery** — forgot-password + reset-password endpoints, JWT tokens, email delivery
- [x] **Rust unit tests** — 7 tests for Customer reducers (create, update, delete, password, tenant isolation), type-check clean, need STDB host runtime to execute
- [x] **Frontend TypeScript tests** — 52 tests: UI components (Button, Card, Badge, Input), Pagination, ErrorBoundary, Auth context, Utils — Vitest + RTL + jsdom
- [x] **E2E tests** — 33 Playwright tests: Navigation (5), Dashboard (6), Customers (7), Invoices (8), Tickets (7) — fake JWT auth, no backend needed
- [x] **Input sanitization** — HTML strip on all 40+ Pydantic models via SanitizedModel base class. Password/token/secret fields excluded. Missing max_length constraints added (10 fields)
- [x] **CI/CD pipeline** — GitHub Actions: build STDB, seed, test (backend + frontend + E2E + Rust check), lint

---

## 🧪 Testing Report

| Area | Status | Details |
|------|--------|---------|
| Rust unit tests | ❌ 0 tests | 70 reducers, 25 tables — zero validation |
| Python backend tests | ✅ 39 tests (624 lines) | Auth, customer CRUD, tickets, tenants, validation |
| TypeScript frontend tests | ✅ 52 tests (8 suites) | Button, Card, Badge, Input, Pagination, ErrorBoundary, Auth, Utils |
| E2E tests | ✅ 33 tests (5 suites) | Navigation, Dashboard, Customers, Invoices, Tickets |
| CI/CD pipeline | ✅ GitHub Actions | build STDB, seed, test (backend + frontend + Rust check), lint |
| **API path coverage** | **9/26 (35%)** | Auth, customers, tickets, invoices, products, tenants, health, portal, validation |
| **Endpoint coverage** | **~22%** | 39 tests for 123 endpoint registrations |

### Test quality assessment

✅ Positive: tests exercise real API with live STDB, verify actual HTTP responses
✅ Positive: SQL injection, malformed JSON, wrong HTTP methods, and auth gaps tested
⚠️ Negative: no negative tests for business logic (e.g. creating invoice without customer)
⚠️ Negative: no concurrent/multi-user tests for tenant isolation
⚠️ Negative: no performance/load tests for pagination gaps
⚠️ Negative: no test isolation — tests share STDB state (no fresh DB per run)
⚠️ Negative: no contract/API spec tests (no OpenAPI generation)

---

## 🚨 Known Anti-Patterns & Technical Debt

### 🔴 CRITICAL (fix within 2 sprints)

1. **No explicit indexes beyond primary key** — `tenant_id` filters on every query, but no index on `tenant_id` column. O(n) scans per tenant.

2. **User table has no `tenant_id`** — deliberate (cross-tenant admin users) but inconsistent with every other entity. Portal users (customers) have no STDB table.

3. **Frontend uses bare `fetch()`** — no React Query/SWR/tanstack-query. Data refetches on every navigation. No caching, no dedup, no optimistic updates.

4. **WeasyPrint adds 200MB+ to Docker image** — depends on pango/cairo system libs. Alternative: chromium headless HTML→PDF or wkhtmltopdf.

### 🟢 MINOR / Cosmetic

8. **6 `hidden_glob_reexports` warnings** in `lib.rs` — `mod X` shadows `pub use X::*`. No functional impact.

9. **No `Result` return in any reducer** — reducers don't signal success/failure to caller. The API layer infers from HTTP status.

10. **Docker Compose uses `network: host`** — bypasses Docker networking. Works locally but won't scale to multi-host.

---

## 🏆 Feature Gap Analysis vs. RepairShopr / Competitors

| Feature | Our Status | Competitor Status | Our Count |
|---------|:----------:|:-----------------:|:---------:|
| Customer management | ✅ Complete | ✅ Parity | 25 tables |
| Ticket/repair tracking | ✅ Complete | ✅ Parity | 10 endpoints |
| Invoicing + line items | ✅ Complete | ✅ Parity | Full CRUD |
| Estimates + conversion | ✅ Complete | ✅ Parity | Full CRUD |
| Payment recording | ✅ Complete | ✅ Parity | Stripe + manual |
| Appointment scheduling | ✅ Complete | ✅ Parity | Calendar view |
| Inventory tracking | ✅ Complete | ✅ Parity | Adjustments |
| Purchase orders | ✅ Complete | ✅ Parity | Receiving |
| Time tracking | ✅ Complete | ✅ Parity | Ticket timers |
| Customer portal | ✅ Complete | ✅ Parity | 4 pages |
| Email notifications | ✅ Complete | ✅ Parity | 4 event types |
| SMS notifications | ✅ Configured | ✅ Parity | Twilio |
| Stripe payments | ✅ Basic | ✅ Parity | No saved cards |
| Webhook API | ✅ Complete | ⭐ Ahead | HMAC-signed |
| Reporting | ✅ Basic | ⭐ Partial | No drill-down |
| Custom fields | ✅ Complete | ✅ Parity | Per entity type |
| Repair checklists | ✅ Complete | ✅ Parity | Templates |
| Barcode scanning | ✅ Complete | ✅ Parity | Product lookup |
| Data import/export | ✅ CSV | ✅ Parity | CSV only |
| Multi-tenant | ✅ Complete | ✅ Parity | 25 tables scoped |
| **Tests** | **🟢 Added (124)** | ✅ Expected | **Second sprint** |
| **Pydantic validation** | **🟢 Started** | ✅ Expected | **2/51 endpoints** |
| Mobile app | ❌ Not started | ⭐ Gap | — |
| POS / counter sale | ❌ Not started | ⭐ Gap | — |
| Purchase order approvals | ❌ Not started | ⭐ Gap | — |
| Automated recurring invoices | ❌ Not started | ✅ Gap | — |
| Customer payment methods | ❌ Not started | ✅ Gap | — |
| Inventory barcode labels | ❌ Not started | ✅ Gap | — |
| Multi-currency | ❌ Not started | ⭐ Gap | — |
| 2FA / SSO | ❌ Not started | ⭐ Gap | — |
| API rate limiting | ❌ Not started | ⭐ Gap | — |
| SLA tracking | ❌ Not started | ⭐ Gap | — |
| Offline mode | ❌ Not started | ❌ Not priority | — |

### Verdict

**Feature parity: ~75% vs RepairShopr core.** The gap is in depth, not breadth — we have most features but they're thinner. The biggest production gaps (tests, validation, pagination) are being closed this sprint.

---

## 🎯 Recommended Next Priority

1. **Add React Query** for data fetching with caching — eliminates bare fetch() calls, enables optimistic updates, request dedup.
2. **WeasyPrint alternative** — evaluate chromium/wkhtmltopdf to reduce Docker image size (~200MB savings).
