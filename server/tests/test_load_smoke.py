"""Performance/load smoke tests for the SpacetimeCRM API.

Closes the ROADMAP test-quality gap "No performance/load tests".

These are NOT benchmarks — they are lightweight regression detectors for
N+1 queries and full-table scans. They fire a burst of concurrent
requests at the two read-heavy dashboard endpoints (``/api/stats`` and
``/api/customers``) and assert that:

1. Every request succeeds (HTTP 200) — no 5xx under concurrency.
2. The p95 latency stays under a generous 3-second budget. There are no
   hard latency assertions below 500ms, so the test is not flaky on slow
   CI runners.

``/api/stats`` issues several full-table SELECTs (customer, ticket,
invoices, payment, appointment) per request, so a query that regresses
to a full-table scan or N+1 pattern will blow the p95 budget and fail
here.

Requires live STDB (:3001) + backend (:8723, or CRM_TEST_SERVER
override) — skips gracefully when the server is unavailable, mirroring
the module-level availability check in test_client.py.
"""

import asyncio
import time

import httpx
import pytest

from .conftest import SERVER_URL

# ── Module-level availability gate ─────────────────────────────────
# Mirror test_client.py: skip the whole module when the CRM server is
# not reachable, so the suite still passes in bare environments.

try:
    _resp = httpx.get(f"{SERVER_URL}/api/health", timeout=3)
    _SERVER_OK = _resp.status_code < 500
except Exception:
    _SERVER_OK = False

if not _SERVER_OK:
    pytest.skip(
        "CRM server not available -- skipping load smoke tests",
        allow_module_level=True,
    )

# Concurrency level for the burst (task requires 10-20 parallel requests).
_BURST = 16  # 8 x /api/stats + 8 x /api/customers
_P95_BUDGET_S = 3.0  # generous p95 latency budget in seconds


def _p95(durations: list[float]) -> float:
    """Return the 95th-percentile latency of a duration list (seconds)."""
    ordered = sorted(durations)
    if not ordered:
        return 0.0
    idx = min(len(ordered) - 1, int(0.95 * len(ordered)))
    return ordered[idx]


@pytest.mark.slow
class TestLoadSmoke:
    """Concurrent smoke tests for read-heavy endpoints."""

    async def test_concurrent_stats_and_customers_within_p95_budget(
        self, auth_headers: dict
    ):
        """A 16-way parallel burst must succeed with p95 < 3s and no 5xx."""
        headers = {"Authorization": auth_headers["Authorization"]}
        # Rotate through the two endpoints so load is interleaved.
        paths = ["/api/stats", "/api/customers"]
        plan = [paths[i % 2] for i in range(_BURST)]

        statuses: list[int] = []
        durations: list[float] = []

        async with httpx.AsyncClient(base_url=SERVER_URL, timeout=15) as client:

            async def hit(path: str) -> tuple[int, float]:
                started = time.perf_counter()
                try:
                    resp = await client.get(path, headers=headers)
                    return resp.status_code, time.perf_counter() - started
                except Exception:
                    # Network/connect errors surface as 599 (never a 5xx).
                    return 599, time.perf_counter() - started

            results = await asyncio.gather(*[hit(p) for p in plan])

        for status, elapsed in results:
            statuses.append(status)
            durations.append(elapsed)

        assert len(results) == _BURST

        # (2) No 5xx under concurrency — every request must succeed.
        failures = [(p, s) for p, s in zip(plan, statuses, strict=True) if s != 200]
        assert not failures, (
            f"Concurrent load produced non-200 responses: {failures}"
        )
        assert all(s < 500 for s in statuses), "5xx detected under concurrency"

        # (1) Generous p95 budget — regression detector, not a benchmark.
        p95 = _p95(durations)
        assert p95 < _P95_BUDGET_S, (
            f"p95 latency {p95:.2f}s exceeded {_P95_BUDGET_S}s budget "
            f"(max {max(durations):.2f}s, min {min(durations):.2f}s) — "
            "possible N+1 / full-table-scan regression"
        )

    async def test_stats_and_customers_succeed_serially(self, auth_headers: dict):
        """Baseline sanity: each endpoint works on its own, no concurrency."""
        headers = {"Authorization": auth_headers["Authorization"]}
        async with httpx.AsyncClient(base_url=SERVER_URL, timeout=15) as client:
            for path in ("/api/stats", "/api/customers"):
                resp = await client.get(path, headers=headers)
                assert resp.status_code == 200, (
                    f"{path} returned {resp.status_code}: {resp.text[:200]}"
                )
