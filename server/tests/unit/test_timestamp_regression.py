"""Regression tests for time-stamp correctness in API routes.

History: several routes computed "now" with patterns that are wrong on
non-UTC servers or in long-running processes:

- ``datetime.utcnow().timestamp()`` — on a naive datetime, ``.timestamp()``
  interprets the value as *local* time. On a server in America/New_York
  (UTC-4) this produced timestamps 4 hours in the future, breaking invoice
  overdue detection, dashboard aggregates, and report schedules.
- ``asyncio.get_event_loop().time()`` — monotonic time since loop start,
  not unix epoch. Used as a unix-ms "now" it broke gift card expiry and
  SLA breach detection.

These tests scan the route sources to prevent regressions.
"""

from __future__ import annotations

import re
from pathlib import Path

ROUTES_DIR = Path(__file__).resolve().parent.parent.parent / "routes"

BAD_EPOCH_MS_PATTERNS = [
    # naive UTC datetime interpreted as local by .timestamp()
    re.compile(r"datetime\.utcnow\(\)\s*\.\s*timestamp\(\)"),
    # monotonic clock used as unix epoch milliseconds
    re.compile(r"get_event_loop\(\)\s*\.\s*time\(\)\s*\*\s*1000"),
    re.compile(r"loop\.time\(\)\s*\*\s*1000"),
]

# Files that legitimately use datetime.utcnow() for JWT exp/iat
# (PyJWT treats naive datetimes as UTC) or display-only strftime.
ALLOWED_UTCnow_FILES = {
    "auth.py",  # JWT exp/iat, temp tokens
    "portal.py",  # JWT exp/iat
    "report_schedules.py",  # display-only strftime in HTML
    "report_schedules_helpers.py",  # display-only strftime
}


def test_no_bad_epoch_patterns_in_routes():
    """Route files must not compute 'now' with naive-UTC or monotonic clocks."""
    offenders = []
    for f in sorted(ROUTES_DIR.glob("*.py")):
        if f.name == "__init__.py":
            continue
        text = f.read_text()
        for pattern in BAD_EPOCH_MS_PATTERNS:
            for m in pattern.finditer(text):
                line_no = text[: m.start()].count("\n") + 1
                offenders.append(f"{f.name}:{line_no}: {m.group(0).strip()}")
    assert not offenders, "Bad time-stamp patterns found:\n" + "\n".join(offenders)


def test_utcnow_only_for_jwt_or_display():
    """datetime.utcnow() is only acceptable in JWT/display contexts.

    auth.py and portal.py use it for JWT exp/iat (PyJWT treats naive
    datetimes as UTC) — verified correct. report_schedules* use it only
    in strftime for display. Any OTHER file must not use it.
    """
    offenders = []
    for f in sorted(ROUTES_DIR.glob("*.py")):
        if f.name == "__init__.py":
            continue
        if f.name in ALLOWED_UTCnow_FILES:
            continue
        text = f.read_text()
        for line_no, line in enumerate(text.splitlines(), 1):
            if "utcnow" in line:
                offenders.append(f"{f.name}:{line_no}: {line.strip()}")
    assert not offenders, "datetime.utcnow() used outside JWT/display:\n" + "\n".join(offenders)
