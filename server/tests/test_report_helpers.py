"""
Regression tests for scheduled-report data building.

Verifies _build_report_data produces valid output for every report type
against the live STDB module (STDB SQL supports no JOINs / ORDER BY /
bind params — the queries must be plain tenant-scoped SELECTs).
"""

import pytest
from routes.report_helpers import _build_report_data

from .conftest import create_customer, unique_suffix

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]


def _make_customer(test_admin_headers: dict, session_suffix: str) -> dict:
    email = f"report-{session_suffix}-{unique_suffix()}@example.com"
    return create_customer(
        test_admin_headers,
        session_suffix=session_suffix,
        first_name="Report",
        last_name="Fixtures",
        email=email,
    )


class TestBuildReportData:
    async def test_revenue_report(self, test_admin_headers: dict, session_suffix: str):
        cust = _make_customer(test_admin_headers, session_suffix)
        tenant_id = cust["tenant_id"]

        data = await _build_report_data("revenue", tenant_id, {})
        assert data["type"] == "revenue"
        assert "total_revenue" in data
        assert "invoice_count" in data
        assert isinstance(data["rows"], list)

    async def test_tickets_report(self, test_admin_headers: dict, session_suffix: str):
        cust = _make_customer(test_admin_headers, session_suffix)
        tenant_id = cust["tenant_id"]

        data = await _build_report_data("tickets", tenant_id, {"status": "open"})
        assert data["type"] == "tickets"
        assert "open" in data
        assert isinstance(data["rows"], list)
        # All rows must survive the status filter
        for row in data["rows"]:
            assert str(row.get("status", "")).lower() == "open"

    async def test_payments_report(self, test_admin_headers: dict, session_suffix: str):
        cust = _make_customer(test_admin_headers, session_suffix)
        tenant_id = cust["tenant_id"]

        data = await _build_report_data("payments", tenant_id, {})
        assert data["type"] == "payments"
        assert "total_collected" in data
        assert isinstance(data["rows"], list)

    async def test_products_report(self, test_admin_headers: dict, session_suffix: str):
        cust = _make_customer(test_admin_headers, session_suffix)
        tenant_id = cust["tenant_id"]

        data = await _build_report_data("products", tenant_id, {})
        assert data["type"] == "products"
        assert "total_products" in data
        assert "low_stock_count" in data
        assert isinstance(data["rows"], list)

    async def test_unknown_report_type(self, test_admin_headers: dict, session_suffix: str):
        cust = _make_customer(test_admin_headers, session_suffix)
        tenant_id = cust["tenant_id"]

        data = await _build_report_data("nonsense", tenant_id, {})
        assert data["type"] == "unknown"
        assert data["rows"] == []
