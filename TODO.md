# SpacetimeCRM - Technical Debt & TODO Tracker

## Overview
Static analysis found code quality issues across the codebase.
Each item below is tracked as FIXME (must fix), scheduled (has ticket), or removed (stale).

## 🔴 FIXME Items (must fix - security, correctness)
- S104: uvicorn bound to 0.0.0.0 in dev — restrict to 127.0.0.1 for deployments
- S105: Hardcoded JWT secret default — ensure env var override documented
- S701: Jinja2 autoescape=False in helpers.py — mitigated with autoescape=True
- BLE001: Blind except in 33 places — should log exceptions
- B904: 10 raise-without-from-inside-except — should chain exceptions
- S110: 14 try-except-pass — should log or handle
- S608: SQL injection vectors — parameterize queries
- B008: 43 function-call-in-default-argument — move to function body

## 🟡 Scheduled Items (tracked with tickets)
- D103: 98 undocumented public functions — backlog for docs sprint
- ANN201: Missing return type annotations — backlog for type hints sprint
- E501: 68 line-too-long — backlog for formatting
- RUF006: 25 asyncio-dangling-task — backlog for async audit
- DTZ003: 12 call-datetime-utcnow — scheduled for timezone audit
- FAST002: 20 non-annotated FastAPI dependencies — scheduled for FastAPI upgrade

## ✅ Resolved / Removed Items
- S701: Jinja2 autoescape=True applied
- TS7053: TypeScript index errors fixed in BusinessHoursSection.tsx
- S105: False positives noted with nosec comments
