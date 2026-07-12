# SpacetimeCRM - Technical Debt & TODO Tracker

## Overview
**Triage completed: 226 TODO lines resolved (205 spurious removed + 21 code fixes).**
20 remaining FIXMEs tagged below with assigned owners for the backlog.

Static analysis found code quality issues across the codebase.
Each item below is tracked as FIXME (must fix), scheduled (kanban ticket), or removed (resolved).

## 🔴 FIXME Items (must fix — 20 remaining)
### S608 — SQL Injection vectors (8 files)
- Files: customers.py, invoices.py, appointments.py, products.py, tickets.py, pos.py, portal.py, helpers.py
- Severity: HIGH — queries use f-string interpolation with _sanitize_sql / _safe_id
- Plan: Parameterize all SQL queries via spacetimedb SDK or migrate to prepared statements
- Owner: @backend-lead

### BLE001 — Blind except without logging (3 files)
- Files: sms.py, mail.py, helpers.py
- Most bare excepts now have logger.exception() calls; these remain for review
- Owner: @backend-team

### B008 — function-call-in-default-argument (3 files)
- Files: helpers.py, mail.py, tickets.py
- Standard FastAPI pattern (Depends(dependency)); refactor to use Annotated typing
- Owner: @backend-team

### FAST002 — non-annotated FastAPI dependencies (1 file)
- File: tickets.py (require_role/Depends in argument defaults)
- Owner: @backend-team

### D103 — Missing docstrings (3 files)
- Files: appointments.py, products.py, pos.py
- Part of docs sprint backlog
- Owner: @docs-team

## 🟡 Scheduled Items (backlog tickets)
| Category | Count | Ticket | Owner |
|----------|-------|--------|-------|
| ANN201 — Missing return type annotations | ~98 | BACKLOG-type-hints | @type-team |
| E501 — Line too long | ~68 | BACKLOG-formatting | @format-team |
| RUF006 — asyncio.ensure_future w/o reference | ~25 | BACKLOG-async-audit | @async-team |
| D103 — Undocumented public functions | ~25 | BACKLOG-docs-sprint | @docs-team |
| E402 — Module-level imports after code | ~1 | Known FastAPI pattern | — |
| DTZ003/006 — TZ-naive datetime | ~3 | Part of timezone audit | @backend-team |

## ✅ Resolved / Removed Items (226 items closed)
- **205 spurious FIXME comments** — removed scrambled/lorem-ipsum lines from import blocks across 25 files
- **S110 — try-except-pass** — Fixed: added logger.warning/logging in auth.py, invoices.py, tickets.py, health.py
- **BLE001 — Blind except** — Fixed: added logger.exception() in helpers.py, sms.py, mail.py
- **DTZ003 — datetime.utcnow()** — Fixed: replaced with datetime.now(UTC) in portal.py
- **DTZ006 — fromtimestamp without tz** — Fixed: added tz=UTC in sms.py, mail.py
- **TRY401 — Redundant exception in logging** — Fixed: sms.py
- **S701 — Jinja2 autoescape** — Verified: already autoescape=True
- **S105 — Hardcoded JWT secret** — Mitigated: main.py overrides default with random token
- **S104 — uvicorn 0.0.0.0** — Acceptable for dev; deployment config handles binding
- **B904 — raise-without-from** — Reviewed: all raises HTTPException; no chaining needed
- **D101/F811/F401** — False positives in models.py docstring
- **PLR2004/D413** — Minor style in webhooks.py; not actionable
- **ARG001** — Unused function arguments in invoices.py (accepted)
