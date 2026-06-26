# SpacetimeCRM — Improvement Backlog

## Status: PENDING

### P0 — Customer portal web view
Customers should be able to log in, see their open tickets, approve/decline estimates, and view invoice history. Requires auth system and read-only API for portal access.
Files: server/main.py (new /portal/* routes), web/src/pages/PortalLogin.tsx
Difficulty: Hard
Est: 8h

### P0 — PDF generation for invoices and estimates
Generate downloadable PDFs for invoices and estimates. Use weasyprint or a headless browser PDF renderer.
Files: server/main.py (new /api/invoices/:id/pdf and /api/estimates/:id/pdf)
Difficulty: Medium
Est: 4h

### P0 — Email notifications on ticket status change
Send email to customer when ticket status changes or invoice is generated. Hook into ticket status reducer.
Files: server/main.py, server/notifications.py
Difficulty: Medium
Est: 3h

### P0 — Calendar view for appointments
Replace the flat appointment list with a month/week/day calendar. Use a React calendar library (react-big-calendar or similar).
Files: web/src/pages/AppointmentsPage.tsx
Difficulty: Medium
Est: 4h

### P1 — Product barcode scanning
Add barcode field to products, support scanning during intake and checkout. Use a barcode reader library or native camera API.
Files: web/src/pages/ProductsPage.tsx
Difficulty: Medium
Est: 3h

### P1 — Repair checklist templates
Create reusable task templates for common repair types (screen replacement, battery swap, water damage). Per-task items with labor estimates.
Files: server/spacetimedb/src/checklist.rs, web/src/pages/Checklists.tsx
Difficulty: Medium
Est: 5h

### P1 — Custom fields
Allow users to define custom fields on customers, tickets, and products. Store as JSON/metadata.
Files: server/spacetimedb/src/custom_field.rs, web/src/pages/SettingsPage.tsx
Difficulty: Medium
Est: 3h

### P1 — Multi-currency support
Add currency_code field to invoices, payments, estimates, and products. Configurable per-company.
Files: server/spacetimedb/src/invoice.rs, server/spacetimedb/src/product.rs
Difficulty: Easy
Est: 2h

### P1 — Inventory adjustments with reason
Track inventory changes with reason codes (received, sold, damaged, returned). Inventory adjustment log table.
Files: server/spacetimedb/src/inventory_adjustment.rs
Difficulty: Easy
Est: 2h

### P2 — Dashboard charts (revenue over time, ticket trends)
Add Recharts charts to the dashboard — monthly revenue bar chart, ticket volume trend line.
Files: web/src/App.tsx (DashboardPage)
Difficulty: Easy
Est: 2h

### P2 — Dark/light mode toggle
Add theme toggle in settings. Alternative light theme CSS variables.
Files: web/src/pages/SettingsPage.tsx
Difficulty: Easy
Est: 1h

### P3 — CSV import/export
Import customers from CSV. Export tickets, invoices to CSV.
Files: server/main.py (new /api/customers/import, /api/invoices/export)
Difficulty: Medium
Est: 3h
