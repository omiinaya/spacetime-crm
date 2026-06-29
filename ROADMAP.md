# SpacetimeCRM — Roadmap & Honest Assessment

**Last assessed:** 2026-06-28
**Overall completeness:** ~65%

---

## 📊 Summary

| Layer | Lines | Completeness | Test Coverage | Anti-Patterns |
|-------|-------|:------------:|:-------------:|:-------------:|
| STDB Module (Rust) | 1,693 | 80% | 0% | 5 major |
| Backend API (Python) | 3,201 | 75% | 0% | 7 major |
| Frontend (TypeScript) | 7,268 | 70% | 0% | 3 major |
| Infra (Docker/scripts) | — | 85% | N/A | 2 minor |
| **Overall** | **12,162** | **65%** | **0%** | **17 items** |

---

## Phase 1: Foundation ✅ (95% complete)

- [x] SpacetimeDB module with 26 tables and reducers
- [x] FastAPI REST server with all CRUD endpoints
- [x] React dashboard with sidebar navigation and dark theme
- [x] Customers page (list, create, edit, delete, search)
- [x] Tickets page (list, create, status workflow, notes)
- [x] Invoices page (list, create, status, line items)
- [x] Payments page (list, record payments)
- [x] Appointments page (schedule, status, CRUD)
- [x] Products page (inventory tracking, low stock alerts)
- [x] Estimates page (quotes with line items)
- [x] Purchase Orders page (vendor ordering)
- [x] Users page (staff management)
- [x] Dashboard stats overview

✅ All core entities have full CRUD. BUT: no pagination on any endpoint, no request validation models, no bulk operations.

---

## Phase 2: Real-World Features ✅ (80% complete)

- [x] Customer portal (web login for customers to view tickets/invoices)
- [x] Customer map (geographic visualization)
- [x] Email notifications (ticket status, invoice reminders)
- [x] PDF generation (invoices, estimates, tickets)
- [x] Calendar view for appointments
- [x] Time tracking with ticket timers
- [x] Inventory adjustments (add/remove stock with reason)
- [x] Purchase order receiving (receive against PO, update stock)
- [x] Tax rate configuration

✅ All Phase 2 features built and wired. BUT: no email templates customization, no recurring appointments, no inventory low-stock alerts (thresholds exist but no notification).

---

## Phase 3: Advanced ✅ (70% complete)

- [x] Multi-tenant support
- [x] SMS notifications (Twilio)
- [x] Stripe payment processing
- [x] Reporting dashboard (revenue by period, tech productivity)
- [x] Barcode scanning for products
- [x] Repair checklist templates
- [x] Custom fields per customer/ticket
- [x] Webhook integration (HMAC-signed, 13 events)
- [ ] 📌 Customer payment methods / saved cards — **NOT IMPLEMENTED**
- [ ] 📌 Portal payment UX — checkout session creates but UI not fully polished
- [ ] 📌 Report scheduling / exports — **NOT IMPLEMENTED**

---

## Phase 4: Production Readiness ⚠️ (40% complete)

- [x] Authentication (JWT login for staff)
- [x] Role-based permissions (admin, tech, front-desk)
- [x] Audit logging (58 calls across all endpoints)
- [x] Data export (CSV)
- [x] Docker Compose for one-command deploy
- [x] Backup/restore scripts
- [x] Health checks and monitoring
- [ ] 🔴 **Tests** — ZERO test files across the entire codebase
- [ ] 🔴 **API input validation** — no Pydantic models anywhere, raw `body: dict`
- [ ] 🔴 **SQL injection risk** — `tenant_id` interpolated via f-strings in 7 `_sql_t()` paths
- [ ] 🔴 **Rate limiting** — none on any endpoint
- [ ] 🔴 **CORS** — set to `["*"]` (too permissive for production)
- [ ] 🔴 **Password recovery** — no forgot-password flow
- [ ] 🟡 **Frontend chunk size** — 980KB single bundle (needs code-splitting)
- [ ] 🟡 **Pagination** — only LIMIT clauses, no offset-based or cursor-based pagination
- [ ] 🟡 **Global exception handlers** — none registered
- [ ] 🟡 **Input sanitization** — raw body passthrough to STDB

---

## 🧪 Testing Report

| Area | Status |
|------|--------|
| Rust unit tests | ❌ 0 tests |
| Python backend tests | ❌ 0 tests |
| TypeScript frontend tests | ❌ 0 tests |
| Integration tests | ❌ 0 tests |
| E2E tests | ❌ 0 tests |
| **Total** | **0 tests across 12,162 lines of code** |

---

## 🚨 Known Anti-Patterns & Technical Debt

### CRITICAL (fix before production)

1. **SQL injection in `_sql_t()`** — `tenant_id` is interpolated directly into SQL via f-strings (`f"AND tenant_id = '{tenant_id}'"`). If tenant_id ever comes from user-controlled input, this is exploitable. Currently tenant_id comes from JWT payload (server-signed), so exposure is limited, but it's still a bad pattern.

2. **No tests** — 12KLOC with zero automated validation. Every deploy is a manual prayer.

3. **No request validation** — every FastAPI endpoint accepts `body: dict` with no schema validation. Malformed payloads pass through to STDB and produce 502 errors instead of 400s.

4. **Incomplete tenant isolation** — 9 places in STDB reducers use `tenant_id: String::new()` instead of propagating the caller's tenant_id:
   - `add_ticket_note`, `start_ticket_timer` (ticket.rs)
   - `add_invoice_line_item`, `add_estimate_line_item`, `convert_estimate_to_invoice` (lib.rs)
   - `add_po_line_item`, `receive_po_item` (purchase_order.rs)
   - `set_custom_field_value` (custom_field.rs)
   - `apply_checklist_template` (checklist.rs)
   
   These create records with blank tenant_id that won't show up in tenant-filtered queries.

5. **CORS `["*"]`** — acceptable for dev, dangerous for production deployment.

### HIGH

6. **Backend is a single 2,481-line file** — `main.py` holds every endpoint, helper, auth function, and middleware. Needs splitting into routes modules.

7. **No pagination** — list endpoints return all rows. With 10K customers this will be a problem.

8. **Frontend chunk size** — 980KB single bundle. Needs React.lazy + Suspense code-splitting per page.

9. **No input sanitization** — raw request bodies go directly to STDB. At minimum SQL escape should be applied.

### MEDIUM

10. **`User` table has no `tenant_id`** — users are not tenant-scoped, which is correct for shared admin users, but inconsistent with every other entity. May cause confusion.

11. **`UserSettings` uses `user_id` as primary key** — fine, but then it _also_ has no `tenant_id`. Settings are per-user so this works, but breaks the pattern.

12. **No `is_default` unique constraint on TaxRate** — default is managed at app level, not enforced by STDB.

13. **No STDB `#[unique]` constraints** — uniqueness for email, slug, etc. is not enforced at the database level.

14. **`webhooks.py` and `mail.py` and `sms.py` use `httpx` inline** — they re-create `AsyncClient` per call instead of sharing a session.

15. **`.cursorrules` still references Supabase** — stale config from before the STDB migration.

16. **Backend uses `jinja2` + `weasyprint` for PDFs** — works but weasyprint is heavy (depends on pango/cairo system libs), Docker image is 200MB+ partly because of this.

17. **No password recovery** — admin passwords can only be set manually.

---

## 🏆 Feature Gap Analysis vs. RepairShopr / Competitors

| Feature | Our Status | Competitor Status | Gap |
|---------|:----------:|:-----------------:|:---:|
| Customer management | ✅ | ✅ | Parity |
| Ticket/repair tracking | ✅ | ✅ | Parity |
| Invoicing + line items | ✅ | ✅ | Parity |
| Estimates + conversion | ✅ | ✅ | Parity |
| Payment recording | ✅ | ✅ | Parity |
| Appointment scheduling | ✅ | ✅ | Parity |
| Inventory tracking | ✅ | ✅ | Parity |
| Purchase orders | ✅ | ✅ | Parity |
| Time tracking | ✅ | ✅ | Parity |
| Customer portal | ✅ | ✅ | Parity |
| Email notifications | ✅ | ✅ | Parity |
| SMS notifications | ✅ | ✅ | Parity |
| Stripe payments | ✅ (basic) | ✅ | Partial — no saved cards, no ACH |
| Webhook API | ✅ | ✅ | Parity |
| Reporting | ✅ (basic) | ⭐ | Partial — no saved reports, no scheduling, no drill-down |
| Custom fields | ✅ | ✅ | Parity |
| Check lists | ✅ | ✅ | Parity |
| Barcode scanning | ✅ | ✅ | Parity |
| Data import/export | ✅ (CSV) | ✅ | Parity |
| Multi-tenant | ✅ | ✅ | Parity |
| Mobile app | ❌ | ⭐ | Gap |
| POS / counter sale | ❌ | ⭐ | Gap |
| Purchase order approvals | ❌ | ⭐ | Gap |
| Automated recurring invoices | ❌ | ✅ | Gap |
| Customer payment methods | ❌ | ✅ | Gap |
| Inventory barcode labels | ❌ | ✅ | Gap |
| Multi-currency | ❌ | ⭐ | Gap |
| 2FA / SSO | ❌ | ⭐ | Gap |
| Offline mode | ❌ | ❌ | Not a priority |
| API rate limiting | ❌ | ⭐ | Gap |
| SLA tracking | ❌ | ⭐ | Gap |

**Verdict:** We have broad feature parity with RepairShopr's core offering (~80% of features covered), but lack depth in some areas (reporting, payments UX, mobile) and are missing a few key items (recurring invoices, saved payment methods, counter POS).

---

## 🎯 Recommended Next Priority

1. **Add tests** — this is the single biggest risk. Start with API integration tests (they exercise the most code per test).
2. **Fix SQL injection** in `_sql_t()` — use parameterized queries.
3. **Add Pydantic request models** — stop accepting `body: dict` everywhere.
4. **Fix tenant isolation gaps** — propagate `tenant_id` to nested creates.
5. **Code-split frontend** — reduce bundle size from 980KB.
6. **Add pagination** to all list endpoints.
