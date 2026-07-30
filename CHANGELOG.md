# Changelog

All notable changes to SpacetimeCRM will be documented in this file.

## [2.0.1] — 2026-07-31

### Fixed
- **Test Collection Errors**: 14 tests failing with `ModuleNotFoundError: No module named 'server'` — added `server/__init__.py` and `pythonpath` in pyproject.toml.
- **SLA Route Capture**: `GET /api/tickets/sla-targets`, `sla-settings`, `sla-breached` were captured by `{ticket_id}` path parameter due to route ordering. Moved SLA routes before `{ticket_id}` definition.
- **Entity Creation Return Values**: `POST /api/tickets`, `/api/invoices`, `/api/users` now return `{"ok": true, "id": "..."}` instead of just `{"ok": true}`. Portal test helpers updated to use the `id` field.
- **Duplicate Email User Creation**: `POST /api/users` now checks for existing email in Python layer before calling STDB reducer, returning `400` instead of `502`.
- **Report Schedule Validation Tests**: Updated expectations from `400` to `422` to match Pydantic validation behavior.
- **Silent Error Handling**: DashboardPage appointment/payment mutations now show `toast.error()`. AuditLogPage shows toast on fetch failure.

### Added
- **Service Type Breakdown**: Revenue reports and dashboard now include invoice/estimate item type breakdown (service vs parts) displayed as PieChart card.
- **Dependabot Configuration**: `.github/dependabot.yml` for automated Python, npm, and GitHub Actions dependency updates.
- **EditorConfig**: `.editorconfig` for cross-editor consistency.
- **Node Version Pin**: `web/.nvmrc` pinning Node 22.
- **Gift Card Management**: Full STDB table with 5 reducers, 6 API routes (create/lookup/list/redeem/void/by-code), TypeScript client, and admin page with filter/search/copy-code/void. Integrated into POS workflow with gift card sell and redeem.
- **POS Gift Card Payment**: New "Gift Card" payment method option with real-time balance lookup. Gift card redeemed automatically on sale completion. Shows balance, insufficient-balance warning, and code entry field.
- **POS Gift Card Sell**: "Sell Gift Card" toggle button in Sale Details panel — issue gift cards directly from the terminal with amount + optional customer name.
- **Gift Cards Admin Page**: Dedicated page (`GiftCardsPage`) with create form, code lookup with full card info, filter tabs (All/Active/Voided), paginated card list with copy-to-clipboard and void actions. Accessible from sidebar navigation.
- **Email Campaigns**: Admin-only email blast system — compose HTML emails with `{{name}}`/`{{email}}` placeholders, pre-built templates (Promotional, Service Reminder, Seasonal Greeting), customer filter (all/has-email/recent activity), test-send to a single address before full blast. Result summary with sent/failed counts and recipient preview.

### Fixed
- **Debug print in main.py**: Changed `print("[scheduler] All tasks stopped")` to proper `logger.info()` call. Added `import logging` + `logger = logging.getLogger(__name__)` to main.py.
- **Author identity enforcement**: Corrected git repo-level user config to `omiinaya <omiinaya@gmail.com>`. Updated memory with the working pattern (`--author` flag, not env vars).
- **Unused import in email_campaigns.py**: Removed `_paginated` import flagged by linter.

### Tests
- **Gift card unit tests**: 18 tests covering code generation (prefix, length, uniqueness, alphanumeric), create validation (rejects zero/negative, accepts valid amounts), redeem validation (missing code, invalid amount, active/inactive card, insufficient balance), and mock integration (code passed to reducer).
- **Email campaign unit tests**: 16 tests covering validation (requires subject/body, placeholder substitution for `{{name}}`/`{{email}}`, default name fallback), send_email mock integration, customer filter SQL clause logic (all, with_email, recent activity).

## [2.0.0] — 2026-07-30

### Added
- **Stock Count Sheets**: Jinja2 template + API endpoint (`GET /api/products/count-sheet`) with category/location filtering. Print-ready HTML for physical inventory counts.
- **Technician Schedule View**: Month-navigation calendar with per-tech appointment filtering. Day-grouped cards with status badges.
- **Product Location Filter**: Filter products by storage location via dropdown on ProductsPage.
- **Service Type Breakdown**: Revenue reports now include invoice/estimate item type breakdown (service vs part vs labor) displayed as pie chart.
- **Structured Logging**: JSON log output for production (configurable via `STRUCTURED_LOGGING=true` env var). Dev mode remains human-readable. 20 unit tests.
- **Ruff Configuration**: `ruff.toml` with curated ruleset. Zero lint errors across all Python code.
- **Pyproject.toml**: Python project metadata + pytest/config settings.
- **OpenAPI Documentation**: Enriched FastAPI app metadata (version, description, contact, license). Docs available at `/docs` and `/redoc`.
- **Git Hooks**: Commit message linting (conventional commits) via `.githooks/commit-msg`.
- **CI Workflow**: Automated lint check on push/PR to main/dev branches.
- **Negative Tests**: 6 new API validation tests covering empty fields, missing fields, auth enforcement, and not-found responses.
- **Error Boundary**: Reusable React `ErrorBoundary` wrapping all pages with collapsible error details + retry button.

### Fixed
- **TypeScript Compilation**: Resolved 7 TS errors across 5 files (misaligned Recharts formatter types, missing function parameters, incorrect prop types). Zero TS errors.
- **Stripe Payments**: Fixed `NameError: stripe_lib not defined` in `init_stripe()` — missing inline import. All 23 stripe unit tests pass.
- **Stripe Test Patches**: Fixed 6 test patches targeting incorrect module paths (`stripe_payments.stripe_lib.*` → function-scoped inline imports). All stripe tests now pass.
- **Catch Handler Types**: Fixed 26 `catch (e: any)` → `catch (e: unknown)` with proper error handling across 12 frontend files.
- **Silent API Errors**: Dashboard stats, ticket timers, and checklist load failures now show toast notifications instead of silent failures.
- **Playwright Import**: Added try/except guard in `pdf.py` to prevent import errors when Playwright is not installed.
- **Ambiguous Unicode**: Replaced en-dash characters with regular hyphens in auth error messages.

### Changed
- **Product Quantity Form**: Added `reorder_quantity` field to product creation/display.
- **Dashboard Revenue Target**: Replaced hardcoded $25k target with configurable runtime setting via Settings page.
- **POS Quick-Cash**: "Exact" button pre-fills amount tendered with cart total for one-tap checkout.
- **Ticket Print View**: Printer-friendly summary of ticket details.
- **PortalDashboard Error Handling**: Silent catch replaced with toast notification.
- **AuditLogPage Type Safety**: `e: any` → `e: AuditLogEntry` with proper import.

### Removed
- **Redundant logging.basicConfig**: Removed from `helpers.py` (replaced by `log_config.py` initialization in `main.py`).

### Security
- **Customer Portal Password Hash**: Stripped from all API responses via `_safe_customer()` helper.
- **Sensitive Field Protection**: Centralized exclude list `CUSTOMER_SENSITIVE_FIELDS` in helpers.
