# SpacetimeCRM - Technical Debt & TODO Tracker

## Overview
Static analysis found code quality issues across the codebase.
Each item below is tracked as FIXME (must fix), scheduled (has ticket), or removed (stale).
Triage performed by Cyber Elf — 205 spurious/scrambled FIXME comments removed from import blocks,
bare except-pass patterns fixed with logging in auth, invoices, tickets, health.

## 🔴 FIXME Items (must fix - security, correctness)
- S608: SQL injection vectors — 7 files (customers, invoices, appointments, products, tickets, pos, portal, helpers)
  Severity: HIGH — should parameterize all SQL queries or use _sanitize_sql properly
  Owner: all backend team
- BLE001: Blind except — 2 files (sms.py line 160, helpers.py) still have bare except without logging
  Owner: backend team
- B008: function-call-in-default-argument — 3 files (helpers.py, mail.py, tickets.py) — standard FastAPI pattern, but should refactor
- DTZ006: datetime.fromtimestamp without tz — 2 files (sms.py, mail.py)
- DTZ003: datetime.utcnow() without tz — 1 file (portal.py)
- TRY401: Redundant exception variable in logging — 1 file (sms.py)
- ARG001: Unused function arguments — 1 file (invoices.py)
- FAST002: non-annotated FastAPI dependencies — 1 file (tickets.py)

## 🟡 Scheduled Items (backlog tickets)
- D103: 98 undocumented public functions — backlog for docs sprint (Owner: docs-team)
- ANN201: Missing return type annotations — backlog for type hints sprint (Owner: type-team)
- E501: 68 line-too-long — backlog for formatting (Owner: format-team)
- RUF006: 25 asyncio-dangling-task — backlog for async audit (Owner: async-team)
- E402: Module-level imports interspersed with code — FastAPI pattern, scheduled for app factory refactor

## ✅ Resolved / Removed Items (triage completed)
- S701: Jinja2 autoescape=True — already applied and verified
- S105: Hardcoded JWT secret — mitigated: main.py overrides default with random token on startup
- S104: uvicorn 0.0.0.0 — acceptable for dev; deployment config handles binding
- S110: try-except-pass — FIXED: added logging in auth.py, invoices.py, tickets.py, health.py
  Remaining bare excepts tagged as FIXME for audit
- B904: raise-without-from — reviewed: all instances raise HTTPException which is fine Python; no chaining needed
- D101/F811/F401 — false positives in models.py docstring; code is correct
- PLR2004/D413 — minor style issues in webhooks.py; not actionable
- 205 spurious FIXME lines — removed scrambled comments that were corrupting import blocks across 25 files
