# Changelog

All notable changes to SpacetimeCRM will be documented in this file.

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
