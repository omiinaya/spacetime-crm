# SpacetimeCRM — Improvement Backlog

## Status: ALL IMPLEMENTED (verified 2026-08-05)

> Every item in this backlog has been implemented and verified against the
> current codebase. The files listed under each item point to the live
> implementation. This file is kept as a record — the scanner should NOT
> re-import these as pending tasks. See AGENTS.md for the current architecture.

### P0 — Customer portal web view ✅ Done
Customers can log in, see their open tickets, approve/decline estimates, and view invoice history.
- Backend: `server/routes/portal.py`
- Frontend: `web/src/pages/PortalLoginPage.tsx`, `PortalDashboard.tsx`, `PortalTicketsPage.tsx`, `PortalInvoicesPage.tsx`, `PortalAppointmentsPage.tsx`
- Auth: `web/src/lib/portal-auth.ts`

### P0 — PDF generation for invoices and estimates ✅ Done
Downloadable PDFs for invoices (and estimates/POS) rendered via headless Chromium.
- Backend: `server/pdf.py` (`html_to_pdf` via Playwright/Chromium), `server/routes/invoices.py` (`GET /api/invoices/{invoice_id}/pdf`), `server/routes/pos.py`
- Templates: `server/templates/`

### P0 — Email notifications on ticket status change ✅ Done
Email + SMS sent to customer when ticket status changes or invoice is generated.
- Backend: `server/mail.py` (`_notify_ticket_status_change`, `_notify_invoice_created`, `_notify_appointment_created`), `server/sms.py`
- Hook: `server/routes/tickets.py` (status-change handler calls `_notify_ticket_status_change`), plus `push.send_notification_to_user`

### P0 — Calendar view for appointments ✅ Done
Month calendar view (with day-detail split) replacing the flat list.
- Frontend: `web/src/components/MonthCalendar.tsx`, used in `web/src/pages/AppointmentsPage.tsx`

### P1 — Product barcode scanning ✅ Done
Barcode field on products + scanning during intake/checkout via the BarcodeDetector API.
- Backend: `server/spacetimedb/src/product.rs` (`barcode` field), `server/routes/products.py`
- Frontend: `web/src/pages/ProductsPage.tsx` (BarcodeDetector support + lookups), `web/src/components/BarcodeLabel.tsx`

### P1 — Repair checklist templates ✅ Done
Reusable task templates per repair type with per-task labor estimates.
- Backend: `server/spacetimedb/src/checklist.rs`
- Frontend: `web/src/pages/ChecklistTemplatesPage.tsx` (Settings → System tab, `web/src/pages/SettingsPage.tsx`)

### P1 — Custom fields ✅ Done
User-defined custom fields on customers, tickets, and products.
- Backend: `server/spacetimedb/src/custom_field.rs`
- Frontend: `web/src/pages/CustomFieldsPage.tsx` (Settings → Data & Fields tab)

### P1 — Multi-currency support ✅ Done
`currency` field on invoices, payments, estimates, products; per-company configurable; same-currency enforced on payment/invoice linkage.
- Backend: `server/spacetimedb/src/invoice.rs`, `server/spacetimedb/src/product.rs`, `server/spacetimedb/src/currency.rs` (`validate_currency`); payment/invoice linkage enforce same currency (see git commit `eb6b731`)

### P1 — Inventory adjustments with reason ✅ Done
Inventory adjustments tracked with reason codes (received, sold, damaged, returned).
- Backend: `server/spacetimedb/src/inventory.rs`

### P2 — Dashboard charts (revenue over time, ticket trends) ✅ Done
Recharts bar/line charts for monthly revenue and ticket volume on the dashboard.
- Frontend: `web/src/pages/DashboardPage.tsx` (BarChart, LineChart from `recharts`)

### P2 — Dark/light mode toggle ✅ Done
Theme toggle in settings; light theme via CSS variables.
- Base: `web/src/lib/theme.ts` (`useTheme`, `toggleTheme`, localStorage persistence)
- Toggle: `web/src/App.tsx` (sidebar toggle) and `web/src/pages/settings/UserPreferencesSection.tsx` (Settings → General)

### P3 — CSV import/export ✅ Done
Import customers/products from CSV/XLSX/JSON; export to CSV/XLSX/JSON.
- Backend: `server/routes/export_import.py` (`EXPORT_FORMATS = ("csv", "xlsx", "json")`)

---

### Legacy / Future backlog — ✅ Done (verified 2026-08-05)
The former legacy items are all delivered and live in the app. This section is
kept as a record — the scanner should NOT re-import these as pending tasks.
- Multi-tenant hardening ✅ Done
  - Health: `server/routes/health.py`, `web/src/pages/HealthPage.tsx` (Settings → System)
  - Tenants: `server/spacetimedb/src/tenant.rs`, `server/routes/tenants.py`, `web/src/pages/TenantsPage.tsx` (Settings → System)
  - Agent access: `server/routes/hermes_id_agents.py`, `web/src/pages/AgentAccess.tsx` (Settings → System)
- Recurring invoices ✅ Done
  - Backend: `server/routes/recurring_invoices.py`, `server/spacetimedb/src/recurring_invoice_rule.rs`
  - Frontend: `web/src/pages/RecurringInvoicesPage.tsx` (Invoices → Recurring sub-tab)
- Gift cards ✅ Done
  - Backend: `server/routes/gift_cards.py`, `server/spacetimedb/src/gift_card.rs`
  - Frontend: `web/src/pages/GiftCardsPage.tsx` (Payments → Gift Cards sub-tab)
- Tech schedule ✅ Done
  - Frontend: `web/src/pages/TechnicianSchedulePage.tsx` (Appointments → Tech Schedule sub-tab)