"""Regression tests: request-derived values must be SQL-escaped in every route.

Covers the injection class fixed across routes/ — a payload like
``x' OR '1'='1`` interpolated into an f-string SQL query must never
appear unescaped. We capture the generated SQL with a fake ``_sql``
and assert the payload is doubled-quote escaped and the query is
quote-balanced (can't break out of the literal).

See commit history: "fix(auth): SQL injection on login/portal endpoints"
and the follow-up sweep that escaped ticket_id/invoice_id/status/customer_id
path/query/body params and DB-derived user values.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from helpers import _paginated
from routes import estimates as est_routes
from routes import invoices as inv_routes
from routes import payments as pay_routes
from routes import portal as portal_routes
from routes import products as prod_routes
from routes import tickets as ticket_routes

INJECTION_PAYLOADS = [
    "x' OR '1'='1",
    "x' UNION SELECT * FROM customer --",
]

USER = {"id": "u_1", "tenant_id": "t_1", "name": "admin", "role": "admin"}
CUSTOMER = {"id": "c_1", "first_name": "Test", "last_name": "User", "email": "c@test.com"}


class SqlRecorder:
    """Fake async _sql that records every query and returns no rows."""

    def __init__(self) -> None:
        self.queries: list[str] = []

    async def __call__(self, query: str, *args, **kwargs) -> list[dict]:
        self.queries.append(query)
        return []


async def _noop_call(*args, **kwargs):
    return None


def _assert_escaped(queries: list[str], payload: str) -> None:
    """Assert every recorded query neutralizes the payload.

    _sqlesc doubles single quotes, so the raw payload must never appear
    verbatim; the escaped form must be present and the whole query must
    stay quote-balanced (the value cannot break out of its literal).
    """
    assert queries, "expected at least one SQL query to be issued"
    escaped = payload.replace("'", "''")
    for q in queries:
        assert escaped in q, f"expected escaped payload {escaped!r} in: {q}"
        assert payload not in q, f"raw unescaped payload found in: {q}"
        assert q.count("'") % 2 == 0, f"unbalanced quotes in: {q}"


@pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
class TestPortalEndpoints:
    """Customer-authenticated endpoints — the highest-risk surface."""

    async def test_ticket_detail_escapes_ticket_id(self, monkeypatch, payload):
        rec = SqlRecorder()
        monkeypatch.setattr(portal_routes, "_sql", rec)
        with pytest.raises(Exception):
            await portal_routes.portal_ticket_detail(payload, CUSTOMER)
        _assert_escaped(rec.queries, payload)

    async def test_invoice_detail_escapes_invoice_id(self, monkeypatch, payload):
        rec = SqlRecorder()
        monkeypatch.setattr(portal_routes, "_sql", rec)
        with pytest.raises(Exception):
            await portal_routes.portal_invoice_detail(payload, CUSTOMER)
        _assert_escaped(rec.queries, payload)

    async def test_make_payment_escapes_invoice_id(self, monkeypatch, payload):
        rec = SqlRecorder()
        monkeypatch.setattr(portal_routes, "_sql", rec)
        monkeypatch.setattr(portal_routes, "_call", _noop_call)
        body = SimpleNamespace(invoice_id=payload, amount=10.0, method="card", reference="")
        with pytest.raises(Exception):
            await portal_routes.portal_make_payment(body, CUSTOMER)
        _assert_escaped(rec.queries, payload)

    async def test_pay_with_saved_card_escapes_ids(self, monkeypatch, payload):
        rec = SqlRecorder()
        monkeypatch.setattr(portal_routes, "_sql", rec)
        monkeypatch.setattr(portal_routes, "_call", _noop_call)
        body = SimpleNamespace(invoice_id=payload, payment_method_id=payload)
        with pytest.raises(Exception):
            await portal_routes.portal_pay_with_saved_card(body, CUSTOMER)
        _assert_escaped(rec.queries, payload)


@pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
class TestListFilters:
    """Query-param filters that flow into _paginated WHERE clauses."""

    async def test_list_invoices_filters(self, monkeypatch, payload):
        rec = SqlRecorder()
        monkeypatch.setattr(inv_routes, "_sql", rec)
        monkeypatch.setattr("helpers._sql", rec)
        await inv_routes.list_invoices(
            status=payload, customer_id=payload, offset=0, limit=50, user=USER
        )
        _assert_escaped(rec.queries, payload)

    async def test_list_tickets_filters(self, monkeypatch, payload):
        rec = SqlRecorder()
        monkeypatch.setattr(ticket_routes, "_sql", rec)
        monkeypatch.setattr("helpers._sql", rec)
        await ticket_routes.list_tickets(
            status=payload, customer_id=payload, offset=0, limit=50, user=USER
        )
        _assert_escaped(rec.queries, payload)

    async def test_list_estimates_filter(self, monkeypatch, payload):
        rec = SqlRecorder()
        monkeypatch.setattr(est_routes, "_sql", rec)
        monkeypatch.setattr("helpers._sql", rec)
        await est_routes.list_estimates(status=payload, offset=0, limit=50, user=USER)
        _assert_escaped(rec.queries, payload)

    async def test_list_payments_filter(self, monkeypatch, payload):
        rec = SqlRecorder()
        monkeypatch.setattr(pay_routes, "_sql", rec)
        monkeypatch.setattr("helpers._sql", rec)
        await pay_routes.list_payments(invoice_id=payload, offset=0, limit=50, user=USER)
        _assert_escaped(rec.queries, payload)


@pytest.mark.parametrize("payload", INJECTION_PAYLOADS)
class TestDirectLookups:
    """Path/body params in direct lookups — must escape AND stay tenant-scoped."""

    async def test_barcode_lookup_escaped_and_scoped(self, monkeypatch, payload):
        rec = SqlRecorder()
        monkeypatch.setattr(prod_routes, "_sql", rec)
        with pytest.raises(Exception):
            await prod_routes.lookup_product_by_barcode(payload, USER)
        _assert_escaped(rec.queries, payload)
        assert "tenant_id = 't_1'" in rec.queries[0], "barcode lookup lost tenant scope"

    async def test_convert_estimate_escaped_and_scoped(self, monkeypatch, payload):
        rec = SqlRecorder()
        monkeypatch.setattr(est_routes, "_sql", rec)
        monkeypatch.setattr(est_routes, "_call", _noop_call)
        with pytest.raises(Exception):
            await est_routes.convert_estimate(payload, USER)
        _assert_escaped(rec.queries, payload)
        assert "tenant_id = 't_1'" in rec.queries[0], "estimate convert lost tenant scope"

    async def test_get_ticket_escaped_and_scoped(self, monkeypatch, payload):
        rec = SqlRecorder()
        monkeypatch.setattr(ticket_routes, "_sql", rec)
        with pytest.raises(Exception):
            await ticket_routes.get_ticket(payload, USER)
        _assert_escaped(rec.queries, payload)
        assert "tenant_id = 't_1'" in rec.queries[0], "ticket lookup lost tenant scope"


class TestPaginatedTenantEscape:
    """The shared _paginated helper must escape the tenant_id condition."""

    async def test_paginated_escapes_tenant_id(self, monkeypatch):
        rec = SqlRecorder()
        monkeypatch.setattr("helpers._sql", rec)
        await _paginated("t' OR '1'='1", "customer", offset=0, limit=10)
        _assert_escaped(rec.queries, "t' OR '1'='1")
        assert "tenant_id = 't'' OR ''1''=''1'" in rec.queries[0]
