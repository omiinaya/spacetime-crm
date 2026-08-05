# SpacetimeCRM — Improvement Backlog

## Status: COMPLETE (all items implemented)

> Audit note (2026-08-05): every item below has been implemented and verified
> against the codebase. The last remaining gap — the estimate PDF endpoint
> (`GET /api/estimates/{id}/pdf` + `server/templates/estimate.html`) — was
> added to complete the P0 "PDF generation for invoices and estimates" item.
>
> Full-suite verification (2026-08-05): 512 Python integration tests, 287
> offline unit tests, 97 frontend vitest tests, and 11/11 Rust container
> integration tests all pass against a fresh isolated STDB instance.

### ✅ P0 — Customer portal web view
Customers can log in, see their open tickets, approve/decline estimates, and view invoice history (plus appointments and online payments).
Files: server/routes/portal.py, web/src/pages/PortalLoginPage.tsx, PortalTicketsPage.tsx, PortalInvoicesPage.tsx, PortalDashboard.tsx, PortalAppointmentsPage.tsx
Status: DONE — verified (routes + pages + server/tests/test_portal.py)

### ✅ P0 — PDF generation for invoices and estimates
Downloadable PDFs for invoices AND estimates via Chromium headless (Playwright, replaces weasyprint).
Files: server/routes/invoices.py (`/api/invoices/:id/pdf`), server/routes/estimates.py (`/api/estimates/:id/pdf`), server/pdf.py, server/templates/invoice.html, server/templates/estimate.html
Status: DONE — estimate PDF added 2026-08-05; templates verified to render valid `%PDF` output.

### ✅ P0 — Email notifications on ticket status change
Email + SMS notifications to customers when ticket status changes or invoices are generated.
Files: server/mail.py, server/sms.py, server/routes/tickets.py (`_notify_ticket_status_change`), server/webhooks.py
Status: DONE — verified (mail/sms engines + notification hooks + tests)

### ✅ P0 — Calendar view for appointments
Month calendar view replaces the flat list.
Files: web/src/components/MonthCalendar.tsx, web/src/pages/AppointmentsPage.tsx
Status: DONE — verified

### ✅ P1 — Product barcode scanning
Barcode field on products, by-barcode lookup endpoint, camera scanning via BarcodeDetector during intake/checkout.
Files: server/spacetimedb/src/product.rs, server/routes/products.py (`/api/products/by-barcode/{barcode}`), web/src/pages/ProductsPage.tsx
Status: DONE — verified

### ✅ P1 — Repair checklist templates
Reusable task templates with per-task labor estimates, attachable to tickets.
Files: server/spacetimedb/src/checklist.rs, server/routes/checklists.py, web/src/pages/ChecklistTemplatesPage.tsx
Status: DONE — verified

### ✅ P1 — Custom fields
User-defined custom fields on customers, tickets, and products, stored as JSON.
Files: server/spacetimedb/src/custom_field.rs, server/routes/custom_fields.py, web/src/pages/CustomFieldsPage.tsx
Status: DONE — verified

### ✅ P1 — Multi-currency support
`currency` field (default "USD") on invoices, payments, estimates, and products; per-company configurable.
Files: server/spacetimedb/src/payment.rs, server/models.py, web/src/lib/api.ts, web/src/pages/InvoicesPage.tsx, PaymentsPage.tsx, EstimatesPage.tsx
Status: DONE — verified

### ✅ P1 — Inventory adjustments with reason
Inventory adjustments tracked with reason codes (received, sold, damaged, returned, counted, transferred).
Files: server/spacetimedb/src/inventory.rs
Status: DONE — verified

### ✅ P2 — Dashboard charts (revenue over time, ticket trends)
Recharts monthly revenue bar chart + ticket volume/status pie on the dashboard.
Files: web/src/pages/DashboardPage.tsx, web/src/pages/ReportsPage.tsx
Status: DONE — verified

### ✅ P2 — Dark/light mode toggle
Theme toggle in settings with instant app-wide sync.
Files: web/src/lib/theme.ts, web/src/pages/SettingsPage.tsx, web/src/App.tsx
Status: DONE — verified

### ✅ P3 — CSV import/export
CSV import for customers/products, CSV export for tickets/invoices/estimates/etc.
Files: server/routes/export_import.py (`/api/import/customers`, `/api/import/products`, `/api/export/{entity}`), web/src/pages/ImportExportPage.tsx
Status: DONE — verified
