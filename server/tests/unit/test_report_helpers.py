"""Unit tests for server/routes/report_helpers.py.

Tests _generate_and_deliver, _calc_next_run, _build_report_data,
_filter_rows, and _render_report_email with all mocked dependencies.
No live STDB or server required.
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ===================================================================
# _calc_next_run
# ===================================================================


class TestCalcNextRun:
    """Next-run calculation for daily/weekly/monthly schedules."""

    def test_daily_same_day_future(self) -> None:
        """Daily schedule where target time is later today."""
        from routes.report_helpers import _calc_next_run

        # 2024-06-15 06:00:00 UTC → 1718445600000ms, target hour 8
        dt = datetime(2024, 6, 15, 6, 0, 0)
        ms = int(dt.timestamp() * 1000)
        result = _calc_next_run("daily", {"hour": 8, "minute": 0}, ms)
        expected = datetime(2024, 6, 15, 8, 0, 0)
        assert result == int(expected.timestamp() * 1000)

    def test_daily_target_passed(self) -> None:
        """Daily schedule where target time has already passed today."""
        from routes.report_helpers import _calc_next_run

        dt = datetime(2024, 6, 15, 10, 0, 0)  # 10 AM, past 8 AM target
        ms = int(dt.timestamp() * 1000)
        result = _calc_next_run("daily", {"hour": 8, "minute": 0}, ms)
        expected = datetime(2024, 6, 16, 8, 0, 0)  # tomorrow
        assert result == int(expected.timestamp() * 1000)

    def test_weekly_monday(self) -> None:
        """Weekly schedule for Monday (0) when today is Thursday (3)."""
        from routes.report_helpers import _calc_next_run

        # 2024-06-13 is Thursday (weekday 3), target Monday (0)
        dt = datetime(2024, 6, 13, 6, 0, 0)
        ms = int(dt.timestamp() * 1000)
        result = _calc_next_run(
            "weekly", {"day_of_week": 0, "hour": 8, "minute": 0}, ms
        )
        expected = datetime(2024, 6, 17, 8, 0, 0)  # next Monday
        assert result == int(expected.timestamp() * 1000)

    def test_weekly_same_day_before(self) -> None:
        """Weekly schedule on same day but before the target time."""
        from routes.report_helpers import _calc_next_run

        # 2024-06-17 is Monday (0). At 6 AM, target 8 AM same day.
        dt = datetime(2024, 6, 17, 6, 0, 0)
        ms = int(dt.timestamp() * 1000)
        result = _calc_next_run(
            "weekly", {"day_of_week": 0, "hour": 8, "minute": 0}, ms
        )
        expected = datetime(2024, 6, 17, 8, 0, 0)
        assert result == int(expected.timestamp() * 1000)

    def test_weekly_same_day_passed(self) -> None:
        """Weekly schedule on same day but after target time — skip to next week."""
        from routes.report_helpers import _calc_next_run

        dt = datetime(2024, 6, 17, 10, 0, 0)  # Monday 10 AM, past 8 AM
        ms = int(dt.timestamp() * 1000)
        result = _calc_next_run(
            "weekly", {"day_of_week": 0, "hour": 8, "minute": 0}, ms
        )
        expected = datetime(2024, 6, 24, 8, 0, 0)  # next Monday
        assert result == int(expected.timestamp() * 1000)

    def test_monthly(self) -> None:
        """Monthly schedule on the 15th."""
        from routes.report_helpers import _calc_next_run

        dt = datetime(2024, 6, 10, 6, 0, 0)
        ms = int(dt.timestamp() * 1000)
        result = _calc_next_run(
            "monthly", {"day_of_month": 15, "hour": 8, "minute": 0}, ms
        )
        expected = datetime(2024, 6, 15, 8, 0, 0)
        assert result == int(expected.timestamp() * 1000)

    def test_monthly_target_passed(self) -> None:
        """Monthly schedule where target day has passed — next month."""
        from routes.report_helpers import _calc_next_run

        dt = datetime(2024, 6, 20, 6, 0, 0)  # past the 15th
        ms = int(dt.timestamp() * 1000)
        result = _calc_next_run(
            "monthly", {"day_of_month": 15, "hour": 8, "minute": 0}, ms
        )
        expected = datetime(2024, 7, 15, 8, 0, 0)  # next month
        assert result == int(expected.timestamp() * 1000)

    def test_monthly_caps_at_28(self) -> None:
        """Monthly schedule should cap day_of_month at 28."""
        from routes.report_helpers import _calc_next_run

        dt = datetime(2024, 1, 15, 6, 0, 0)
        ms = int(dt.timestamp() * 1000)
        result = _calc_next_run(
            "monthly", {"day_of_month": 31, "hour": 8, "minute": 0}, ms
        )
        expected = datetime(2024, 1, 28, 8, 0, 0)  # capped at 28
        assert result == int(expected.timestamp() * 1000)

    def test_monthly_rolls_to_january(self) -> None:
        """Monthly schedule rolling from December to January."""
        from routes.report_helpers import _calc_next_run

        dt = datetime(2024, 12, 20, 6, 0, 0)
        ms = int(dt.timestamp() * 1000)
        result = _calc_next_run(
            "monthly", {"day_of_month": 15, "hour": 8, "minute": 0}, ms
        )
        expected = datetime(2025, 1, 15, 8, 0, 0)
        assert result == int(expected.timestamp() * 1000)

    def test_unknown_frequency_defaults_to_tomorrow(self) -> None:
        """Unknown frequency should default to +1 day."""
        from routes.report_helpers import _calc_next_run

        dt = datetime(2024, 6, 15, 6, 0, 0)
        ms = int(dt.timestamp() * 1000)
        result = _calc_next_run("yearly", {"hour": 8, "minute": 0}, ms)
        expected = datetime(2024, 6, 16, 6, 0, 0)  # just +1 day
        assert result == int(expected.timestamp() * 1000)


# ===================================================================
# _filter_rows
# ===================================================================


class TestFilterRows:
    """Case-insensitive row filtering."""

    def test_matches_field(self) -> None:
        from routes.report_helpers import _filter_rows

        rows = [
            {"status": "Open", "title": "Fix printer"},
            {"status": "closed", "title": "Replace cable"},
        ]
        result = _filter_rows(rows, "status", "open")
        assert len(result) == 1
        assert result[0]["title"] == "Fix printer"

    def test_no_match(self) -> None:
        from routes.report_helpers import _filter_rows

        rows = [{"status": "closed", "title": "Done"}]
        result = _filter_rows(rows, "status", "open")
        assert result == []

    def test_empty_rows(self) -> None:
        from routes.report_helpers import _filter_rows

        assert _filter_rows([], "status", "open") == []

    def test_case_insensitive(self) -> None:
        from routes.report_helpers import _filter_rows

        rows = [{"status": "OPEN"}, {"status": "Open"}, {"status": "open"}]
        result = _filter_rows(rows, "status", "open")
        assert len(result) == 3

    def test_field_not_in_row(self) -> None:
        from routes.report_helpers import _filter_rows

        rows = [{"name": "Alice", "status": "open"}, {"name": "Bob"}]
        result = _filter_rows(rows, "status", "open")
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    def test_none_field(self) -> None:
        from routes.report_helpers import _filter_rows

        rows = [{"status": None}, {"status": "open"}]
        # str(None) == "None", matching status value "none"
        result = _filter_rows(rows, "status", "none")
        assert len(result) == 1
        assert result[0]["status"] is None

        # No status field -> str(r.get(field, "")) == ""
        result = _filter_rows([{"name": "Alice"}, {"status": "open"}], "status", "")
        assert len(result) == 1
        assert result[0]["name"] == "Alice"


# ===================================================================
# _render_report_email
# ===================================================================


class TestRenderReportEmail:
    """HTML email rendering for each report type."""

    def test_revenue_summary(self) -> None:
        from routes.report_helpers import _render_report_email

        data = {
            "type": "revenue",
            "total_revenue": 12345.67,
            "invoice_count": 10,
            "period": "last_30_days",
            "rows": [["inv-1", "150.00", "paid", "Alice"]],
        }
        html = _render_report_email("revenue", "Revenue Report", data)
        assert "Total Revenue" in html
        assert "$12,345.67" in html
        assert "Invoice Count" in html
        assert "10" in html
        assert "last_30_days" in html

    def test_tickets_summary(self) -> None:
        from routes.report_helpers import _render_report_email

        data = {
            "type": "tickets",
            "total": 25,
            "open": 5,
            "rows": [["TCK-001", "Fix network", "open", "high"]],
        }
        html = _render_report_email("tickets", "Ticket Report", data)
        assert "Total Tickets" in html
        assert "25" in html
        assert "Open" in html
        assert "5" in html
        assert "TCK-001" in html

    def test_payments_summary(self) -> None:
        from routes.report_helpers import _render_report_email

        data = {
            "type": "payments",
            "total_collected": 5000.00,
            "payment_count": 8,
            "rows": [["pmt-1", "cc", "2024-06-01", "Bob"]],
        }
        html = _render_report_email("payments", "Payment Report", data)
        assert "Total Collected" in html
        assert "$5,000.00" in html
        assert "Payments" in html
        assert "8" in html

    def test_inventory_summary(self) -> None:
        from routes.report_helpers import _render_report_email

        data = {
            "type": "inventory",
            "total_products": 100,
            "low_stock_count": 3,
            "rows": [["Widget", "WDG-001", "10", "15.00"]],
        }
        html = _render_report_email("inventory", "Inventory Report", data)
        assert "Total Products" in html
        assert "100" in html
        assert "Low Stock" in html
        assert "3" in html

    def test_products_summary(self) -> None:
        from routes.report_helpers import _render_report_email

        data = {
            "type": "products",
            "total_products": 50,
            "low_stock_count": 0,
            "rows": [],
        }
        html = _render_report_email("products", "Products Report", data)
        assert "Total Products" in html
        assert "Low Stock" in html
        assert "0" in html

    def test_unknown_type_has_no_summary(self) -> None:
        from routes.report_helpers import _render_report_email

        data = {"type": "unknown", "rows": []}
        html = _render_report_email("unknown", "Unknown Report", data)
        assert "Scheduled Report" not in html  # no summary HTML
        assert "SpacetimeCRM" in html  # footer present
        assert "Unknown Report" in html  # title present

    def test_empty_rows(self) -> None:
        from routes.report_helpers import _render_report_email

        data = {
            "type": "revenue",
            "total_revenue": 0,
            "invoice_count": 0,
            "period": "all",
            "rows": [],
        }
        html = _render_report_email("revenue", "Revenue Report", data)
        assert "$0.00" in html
        assert "<table" in html
        assert "</table>" in html

    def test_none_values_in_rows(self) -> None:
        from routes.report_helpers import _render_report_email

        data = {
            "type": "revenue",
            "total_revenue": 100,
            "invoice_count": 1,
            "period": "all",
            "rows": [["inv-1", None, "paid", None]],
        }
        html = _render_report_email("revenue", "Revenue Report", data)
        # None cells rendered as empty string
        assert "<td" in html
        assert "" in html  # the empty string for None cells


# ===================================================================
# _build_report_data
# ===================================================================


class MockRowResult:
    """Helper to create mock _sql results as a list of tuples."""

    @staticmethod
    def as_tuples(*rows: tuple):
        return [
            {"rows": [list(r) for r in rows], "schema": {"elements": []}} for _ in [1]
        ][0]


class TestBuildReportData:
    """Report data fetching for different report types."""

    @pytest.mark.asyncio
    async def test_revenue_report(self) -> None:
        """Revenue report should sum invoice totals for paid/sent statuses."""
        mock_rows = [
            [100.0, "2024-06-01", "paid", "Alice"],
            [50.0, "2024-06-02", "sent", "Bob"],
            [25.0, "2024-06-03", "draft", "Charlie"],  # excluded
        ]

        with patch("routes.report_helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = mock_rows
            result = await _build_report_data(
                "revenue", "tenant-1", {"period": "last_30_days"}
            )

        assert result["type"] == "revenue"
        assert result["total_revenue"] == 150.0  # 100 + 50
        assert result["invoice_count"] == 3
        assert result["period"] == "last_30_days"
        assert len(result["rows"]) == 3
        mock_sql.assert_called_once()

    @pytest.mark.asyncio
    async def test_tickets_report_no_filter(self) -> None:
        """Tickets report without status filter."""
        mock_rows = [
            ["TCK-1", "Issue A", "open", "high", "2024-06-01", "Alice"],
            ["TCK-2", "Issue B", "closed", "low", "2024-06-02", "Bob"],
            ["TCK-3", "Issue C", "in_progress", "medium", "2024-06-03", "Charlie"],
        ]

        with patch("routes.report_helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = mock_rows
            result = await _build_report_data("tickets", "tenant-1", {})

        assert result["type"] == "tickets"
        assert result["total"] == 3
        assert result["open"] == 2  # open + in_progress
        assert len(result["rows"]) == 3

    @pytest.mark.asyncio
    async def test_tickets_report_with_status_filter(self) -> None:
        """Tickets report with status filter should filter rows and update counts."""
        mock_rows = [
            ["TCK-1", "Issue A", "open", "high", "2024-06-01", "Alice"],
            ["TCK-2", "Issue B", "closed", "low", "2024-06-02", "Bob"],
        ]

        with patch("routes.report_helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = mock_rows
            result = await _build_report_data(
                "tickets", "tenant-1", {"status": "closed"}
            )

        assert result["type"] == "tickets"
        assert result["total"] == 1  # filtered to only 1 closed ticket
        assert result["open"] == 0  # closed tickets aren't "open"
        assert len(result["rows"]) == 1

    @pytest.mark.asyncio
    async def test_payments_report(self) -> None:
        """Payments report should sum all amounts."""
        mock_rows = [
            [100.0, "cc", "2024-06-01", "Alice"],
            [50.0, "cash", "2024-06-02", "Bob"],
        ]

        with patch("routes.report_helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = mock_rows
            result = await _build_report_data("payments", "tenant-1", {})

        assert result["type"] == "payments"
        assert result["total_collected"] == 150.0
        assert result["payment_count"] == 2
        assert len(result["rows"]) == 2

    @pytest.mark.asyncio
    async def test_inventory_report(self) -> None:
        """Inventory report should identify low stock items."""
        mock_rows = [
            ["Widget", "WDG-001", 3, 15.0, "Parts"],  # low stock (< 5)
            ["Gadget", "GDG-001", 10, 25.0, "Electronics"],  # ok
            ["Bolt", "BLT-001", 1, 0.5, "Hardware"],  # low stock
        ]

        with patch("routes.report_helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = mock_rows
            result = await _build_report_data("inventory", "tenant-1", {})

        assert result["type"] == "inventory"
        assert result["total_products"] == 3
        assert result["low_stock_count"] == 2  # Widget (3) + Bolt (1)
        assert len(result["rows"]) == 3

    @pytest.mark.asyncio
    async def test_inventory_null_quantity_not_low_stock(self) -> None:
        """Products with null quantity should not count as low stock."""
        mock_rows = [
            ["Service", "SRV-001", None, 100.0, "Services"],
        ]

        with patch("routes.report_helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = mock_rows
            result = await _build_report_data("products", "tenant-1", {})

        assert result["type"] == "products"
        assert result["total_products"] == 1
        assert result["low_stock_count"] == 0  # None < 5 is False

    @pytest.mark.asyncio
    async def test_unknown_report_type(self) -> None:
        """Unknown report type should return empty data."""
        with patch("routes.report_helpers._sql", new_callable=AsyncMock):
            result = await _build_report_data("unknown_type", "tenant-1", {})

        assert result["type"] == "unknown"
        assert result["rows"] == []

    @pytest.mark.asyncio
    async def test_sql_failure_propagates(self) -> None:
        """SQL failure should propagate up to caller."""
        with patch("routes.report_helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.side_effect = RuntimeError("STDB unreachable")
            with pytest.raises(RuntimeError, match="STDB unreachable"):
                await _build_report_data("revenue", "tenant-1", {})


# ===================================================================
# _generate_and_deliver
# ===================================================================


class TestGenerateAndDeliver:
    """End-to-end report generation and email delivery."""

    @pytest.mark.asyncio
    async def test_sends_to_all_recipients(self) -> None:
        """Should generate, render, and send to all valid recipients."""
        schedule = {
            "id": "sched-1",
            "name": "Weekly Revenue",
            "report_type": "revenue",
            "recipients_json": json.dumps(
                [
                    {"email": "alice@example.com"},
                    {"email": "bob@example.com"},
                ]
            ),
            "filters_json": json.dumps({"period": "last_week"}),
            "tenant_id": "tenant-1",
        }
        user = {"id": "user-1", "tenant_id": "tenant-1"}

        with (
            patch("routes.report_helpers._sql", new_callable=AsyncMock) as mock_sql,
            patch(
                "routes.report_helpers.send_email", new_callable=AsyncMock
            ) as mock_send,
            patch(
                "routes.report_helpers._log_audit", new_callable=AsyncMock
            ) as mock_audit,
        ):
            mock_sql.return_value = [[100.0, "2024-06-01", "paid", "Alice"]]

            result = await _generate_and_deliver(schedule, user)

        assert result["sent"] == 2
        assert result["failed"] == 0
        assert mock_send.call_count == 2
        assert mock_audit.call_count >= 1  # delivered audit
        # Verify emails sent to both recipients
        emails_sent = {call.kwargs["to"] for call in mock_send.call_args_list}
        assert emails_sent == {"alice@example.com", "bob@example.com"}

    @pytest.mark.asyncio
    async def test_handles_generation_failure(self) -> None:
        """If report generation fails, should log and return error."""
        schedule = {
            "id": "sched-1",
            "name": "Revenue",
            "report_type": "revenue",
            "recipients_json": "[]",
            "filters_json": "{}",
            "tenant_id": "tenant-1",
        }
        user = {"id": "user-1", "tenant_id": "tenant-1"}

        with (
            patch("routes.report_helpers._sql", new_callable=AsyncMock) as mock_sql,
            patch("routes.report_helpers._log_audit", new_callable=AsyncMock),
        ):
            mock_sql.side_effect = ValueError("Bad query")

            result = await _generate_and_deliver(schedule, user)

        assert result["sent"] == 0
        assert result["failed"] == 0
        assert len(result["errors"]) == 1
        assert "Bad query" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_handles_render_failure(self) -> None:
        """If HTML rendering fails, should log and return error."""
        schedule = {
            "id": "sched-1",
            "name": "Tickets",
            "report_type": "tickets",
            "recipients_json": json.dumps([{"email": "alice@example.com"}]),
            "filters_json": "{}",
            "tenant_id": "tenant-1",
        }
        user = {"id": "user-1", "tenant_id": "tenant-1"}

        with (
            patch("routes.report_helpers._sql", new_callable=AsyncMock) as mock_sql,
            patch("routes.report_helpers._render_report_email") as mock_render,
            patch("routes.report_helpers._log_audit", new_callable=AsyncMock),
        ):
            mock_sql.return_value = [
                ["TCK-1", "Issue", "open", "high", "2024-06-01", "Alice"]
            ]
            mock_render.side_effect = TypeError("Can't render")

            result = await _generate_and_deliver(schedule, user)

        assert result["sent"] == 0
        assert len(result["errors"]) == 1
        assert "Can't render" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_skips_empty_recipients(self) -> None:
        """Should skip recipients with no email address."""
        schedule = {
            "id": "sched-1",
            "name": "Revenue",
            "report_type": "revenue",
            "recipients_json": json.dumps(
                [
                    {"email": "alice@example.com"},
                    {"email": ""},
                    {},
                    "bob@example.com",  # string recipient
                ]
            ),
            "filters_json": "{}",
            "tenant_id": "tenant-1",
        }
        user = {"id": "user-1", "tenant_id": "tenant-1"}

        with (
            patch("routes.report_helpers._sql", new_callable=AsyncMock) as mock_sql,
            patch(
                "routes.report_helpers.send_email", new_callable=AsyncMock
            ) as mock_send,
            patch("routes.report_helpers._log_audit", new_callable=AsyncMock),
        ):
            mock_sql.return_value = [[100.0, "2024-06-01", "paid", "Alice"]]

            result = await _generate_and_deliver(schedule, user)

        # alice@example.com and bob@example.com (string) should be sent
        assert result["sent"] == 2

    @pytest.mark.asyncio
    async def test_handles_send_failure(self) -> None:
        """If email sending fails for some recipients, track failures."""
        schedule = {
            "id": "sched-1",
            "name": "Revenue",
            "report_type": "revenue",
            "recipients_json": json.dumps(
                [
                    {"email": "alice@example.com"},
                    {"email": "bob@example.com"},
                ]
            ),
            "filters_json": "{}",
            "tenant_id": "tenant-1",
        }
        user = {"id": "user-1", "tenant_id": "tenant-1"}

        with (
            patch("routes.report_helpers._sql", new_callable=AsyncMock) as mock_sql,
            patch(
                "routes.report_helpers.send_email", new_callable=AsyncMock
            ) as mock_send,
            patch("routes.report_helpers._log_audit", new_callable=AsyncMock),
        ):
            mock_sql.return_value = [[100.0, "2024-06-01", "paid", "Alice"]]
            mock_send.side_effect = [None, RuntimeError("SMTP timeout")]

            result = await _generate_and_deliver(schedule, user)

        assert result["sent"] == 1
        assert result["failed"] == 1
        assert len(result["errors"]) == 1
        assert "SMTP timeout" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_uses_schedule_recipients_as_strings(self) -> None:
        """When recipients are strings (not dicts), send directly."""
        schedule = {
            "id": "sched-1",
            "name": "Revenue",
            "report_type": "revenue",
            "recipients_json": json.dumps(["alice@example.com", "bob@example.com"]),
            "filters_json": "{}",
            "tenant_id": "tenant-1",
        }
        user = {"id": "user-1", "tenant_id": "tenant-1"}

        with (
            patch("routes.report_helpers._sql", new_callable=AsyncMock) as mock_sql,
            patch(
                "routes.report_helpers.send_email", new_callable=AsyncMock
            ) as mock_send,
            patch("routes.report_helpers._log_audit", new_callable=AsyncMock),
        ):
            mock_sql.return_value = [[100.0, "2024-06-01", "paid", "Alice"]]

            result = await _generate_and_deliver(schedule, user)

        assert result["sent"] == 2
        assert result["failed"] == 0


# Import the functions under test at module level for cleaner test usage
from routes.report_helpers import (  # noqa: E402
    _build_report_data,
    _calc_next_run,
    _filter_rows,
    _generate_and_deliver,
    _render_report_email,
)
