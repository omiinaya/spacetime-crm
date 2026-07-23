"""Unit tests for server/routes/report_schedules_helpers.py.

Tests _calc_next_run and _render_report_email in isolation.
No live STDB or FastAPI server needed.
"""

from __future__ import annotations


class TestCalcNextRun:
    """_calc_next_run — next-run timestamp calculations."""

    def _ts(
        self, year: int, month: int, day: int, hour: int = 0, minute: int = 0
    ) -> int:
        """Helper: return unix-ms for a naive local datetime
        (matching _calc_next_run's internal use of datetime.fromtimestamp)."""
        from datetime import datetime as dt_mod

        naive = dt_mod(year, month, day, hour, minute)
        return int(naive.timestamp() * 1000)

    # ── daily ──────────────────────────────────────────────────────

    def test_daily_before_run_time(self) -> None:
        from routes.report_schedules_helpers import _calc_next_run

        # 8:00 AM on Jan 1 → next is same day at 8:00AM if current time < 8AM
        from_ms = self._ts(2026, 1, 1, 7, 0)  # 7:00 AM
        result = _calc_next_run("daily", {"hour": 8}, from_ms)
        expected = self._ts(2026, 1, 1, 8, 0)
        assert result == expected, f"expected {expected}, got {result}"

    def test_daily_after_run_time_rolls_to_next_day(self) -> None:
        from routes.report_schedules_helpers import _calc_next_run

        # 9:00 AM, run hour=8 → next is tomorrow at 8:00 AM
        from_ms = self._ts(2026, 1, 1, 9, 0)  # 9:00 AM
        result = _calc_next_run("daily", {"hour": 8}, from_ms)
        expected = self._ts(2026, 1, 2, 8, 0)
        assert result == expected, f"expected {expected}, got {result}"

    def test_daily_exactly_at_run_time_rolls(self) -> None:
        from routes.report_schedules_helpers import _calc_next_run

        # Exactly 8:00 AM, run hour=8 → next is tomorrow at 8:00 AM
        from_ms = self._ts(2026, 1, 1, 8, 0)
        result = _calc_next_run("daily", {"hour": 8}, from_ms)
        expected = self._ts(2026, 1, 2, 8, 0)
        assert result == expected, f"expected {expected}, got {result}"

    def test_daily_custom_minute(self) -> None:
        from routes.report_schedules_helpers import _calc_next_run

        from_ms = self._ts(2026, 1, 1, 7, 0)
        result = _calc_next_run("daily", {"hour": 14, "minute": 30}, from_ms)
        expected = self._ts(2026, 1, 1, 14, 30)
        assert result == expected

    # ── weekly ─────────────────────────────────────────────────────

    def test_weekly_same_day_earlier(self) -> None:
        from routes.report_schedules_helpers import _calc_next_run

        # Monday 7:00 AM, run Monday 8:00 AM → same day
        from_ms = self._ts(2026, 1, 5, 7, 0)  # Monday Jan 5
        result = _calc_next_run("weekly", {"day_of_week": 0, "hour": 8}, from_ms)
        expected = self._ts(2026, 1, 5, 8, 0)
        assert result == expected

    def test_weekly_same_day_later_rolls_seven(self) -> None:
        from routes.report_schedules_helpers import _calc_next_run

        # Monday 9:00 AM, run Monday 8:00 AM → next Monday
        from_ms = self._ts(2026, 1, 5, 9, 0)  # Monday 9AM
        result = _calc_next_run("weekly", {"day_of_week": 0, "hour": 8}, from_ms)
        expected = self._ts(2026, 1, 12, 8, 0)  # next Monday
        assert result == expected

    def test_weekly_future_day(self) -> None:
        from routes.report_schedules_helpers import _calc_next_run

        # Monday, run Wednesday → Wednesday same week
        from_ms = self._ts(2026, 1, 5, 7, 0)  # Monday
        result = _calc_next_run("weekly", {"day_of_week": 2, "hour": 8}, from_ms)
        expected = self._ts(2026, 1, 7, 8, 0)  # Wednesday
        assert result == expected

    def test_weekly_sunday(self) -> None:
        from routes.report_schedules_helpers import _calc_next_run

        # Saturday, run Sunday → next day
        from_ms = self._ts(2026, 1, 10, 7, 0)  # Saturday
        result = _calc_next_run("weekly", {"day_of_week": 6, "hour": 8}, from_ms)
        expected = self._ts(2026, 1, 11, 8, 0)  # Sunday
        assert result == expected

    # ── monthly ────────────────────────────────────────────────────

    def test_monthly_same_day_earlier(self) -> None:
        from routes.report_schedules_helpers import _calc_next_run

        # Jan 1 7:00 AM, run day 15 → Jan 15
        from_ms = self._ts(2026, 1, 1, 7, 0)
        result = _calc_next_run("monthly", {"day_of_month": 15}, from_ms)
        expected = self._ts(2026, 1, 15, 8, 0)  # default hour=8
        assert result == expected

    def test_monthly_past_day_rolls_to_next_month(self) -> None:
        from routes.report_schedules_helpers import _calc_next_run

        # Jan 20, run day 15 → Feb 15
        from_ms = self._ts(2026, 1, 20, 7, 0)
        result = _calc_next_run("monthly", {"day_of_month": 15}, from_ms)
        expected = self._ts(2026, 2, 15, 8, 0)
        assert result == expected

    def test_monthly_year_rollover(self) -> None:
        from routes.report_schedules_helpers import _calc_next_run

        # Dec 20, run day 15 → Jan 15 next year
        from_ms = self._ts(2026, 12, 20, 7, 0)
        result = _calc_next_run("monthly", {"day_of_month": 15}, from_ms)
        expected = self._ts(2027, 1, 15, 8, 0)
        assert result == expected

    def test_monthly_day_capped_at_28(self) -> None:
        from routes.report_schedules_helpers import _calc_next_run

        # Requesting day 31 gets capped to 28
        from_ms = self._ts(2026, 1, 1, 7, 0)
        result = _calc_next_run("monthly", {"day_of_month": 31}, from_ms)
        expected = self._ts(2026, 1, 28, 8, 0)
        assert result == expected

    def test_monthly_exact_day_rolls(self) -> None:
        from routes.report_schedules_helpers import _calc_next_run

        # Jan 15 at 8AM, run day 15 → Feb 15
        from_ms = self._ts(2026, 1, 15, 8, 0)
        result = _calc_next_run("monthly", {"day_of_month": 15}, from_ms)
        expected = self._ts(2026, 2, 15, 8, 0)
        assert result == expected

    def test_monthly_custom_hour(self) -> None:
        from routes.report_schedules_helpers import _calc_next_run

        from_ms = self._ts(2026, 1, 1, 7, 0)
        result = _calc_next_run("monthly", {"day_of_month": 10, "hour": 14}, from_ms)
        expected = self._ts(2026, 1, 10, 14, 0)
        assert result == expected

    # ── unknown frequency ──────────────────────────────────────────

    def test_unknown_frequency_defaults_to_daily(self) -> None:
        from routes.report_schedules_helpers import _calc_next_run

        from_ms = self._ts(2026, 1, 1, 7, 0)
        result = _calc_next_run("yearly", {}, from_ms)
        # Unknown frequency: just adds 1 day (preserving hour/minute)
        expected = self._ts(2026, 1, 2, 7, 0)
        assert result == expected

    def test_unknown_frequency_custom_defaults(self) -> None:
        from routes.report_schedules_helpers import _calc_next_run

        from_ms = self._ts(2026, 1, 1, 7, 0)
        result = _calc_next_run("fortnightly", {"hour": 12, "minute": 0}, from_ms)
        # Unknown frequency ignores config and just adds 1 day
        expected = self._ts(2026, 1, 2, 7, 0)
        assert result == expected


class TestRenderReportEmail:
    """_render_report_email — HTML email body generation."""

    def test_contains_report_name(self) -> None:
        from routes.report_schedules_helpers import _render_report_email

        html = _render_report_email("revenue", "Weekly Revenue", {"rows": []})
        assert "Weekly Revenue" in html

    def test_contains_generated_timestamp(self) -> None:
        from routes.report_schedules_helpers import _render_report_email

        html = _render_report_email("revenue", "Test", {"rows": []})
        assert "Generated" in html
        assert "UTC" in html

    def test_renders_row_data(self) -> None:
        from routes.report_schedules_helpers import _render_report_email

        data = {
            "rows": [
                ["Widget A", "$100", "Shipped", "2026-01-15"],
                ["Widget B", "$200", "Pending", "2026-01-16"],
            ]
        }
        html = _render_report_email("revenue", "Order Report", data)
        assert "Widget A" in html
        assert "$100" in html
        assert "$200" in html
        assert "Widget B" in html

    def test_handles_none_cell(self) -> None:
        from routes.report_schedules_helpers import _render_report_email

        data = {"rows": [["Item A", None, "OK", "2026-01-15"]]}
        html = _render_report_email("revenue", "Test", data)
        assert "Item A" in html
        assert "OK" in html

    def test_contains_table_structure(self) -> None:
        from routes.report_schedules_helpers import _render_report_email

        html = _render_report_email("revenue", "Test", {"rows": []})
        assert "<table" in html
        assert "<thead>" in html
        assert "<tbody>" in html
        assert "<th" in html

    # ── summary sections ───────────────────────────────────────────

    def test_revenue_summary(self) -> None:
        from routes.report_schedules_helpers import _render_report_email

        data = {
            "type": "revenue",
            "rows": [],
            "total_revenue": 15250.50,
            "invoice_count": 42,
            "period": "2026-Q1",
        }
        html = _render_report_email("revenue", "Q1 Revenue", data)
        assert "Total Revenue" in html
        assert "$15,250.50" in html
        assert "42" in html
        assert "2026-Q1" in html

    def test_tickets_summary(self) -> None:
        from routes.report_schedules_helpers import _render_report_email

        data = {
            "type": "tickets",
            "rows": [],
            "total": 150,
            "open": 23,
        }
        html = _render_report_email("tickets", "Ticket Summary", data)
        assert "Total Tickets" in html
        assert "150" in html
        assert "23" in html

    def test_payments_summary(self) -> None:
        from routes.report_schedules_helpers import _render_report_email

        data = {
            "type": "payments",
            "rows": [],
            "total_collected": 8750.00,
            "payment_count": 31,
        }
        html = _render_report_email("payments", "Payment Summary", data)
        assert "Total Collected" in html
        assert "$8,750.00" in html
        assert "31" in html

    def test_inventory_summary(self) -> None:
        from routes.report_schedules_helpers import _render_report_email

        data = {
            "type": "inventory",
            "rows": [],
            "total_products": 200,
            "low_stock_count": 5,
        }
        html = _render_report_email("inventory", "Stock Report", data)
        assert "Total Products" in html
        assert "200" in html
        assert "Low Stock" in html
        assert "5" in html

    def test_products_summary(self) -> None:
        from routes.report_schedules_helpers import _render_report_email

        data = {
            "type": "products",
            "rows": [],
            "total_products": 150,
            "low_stock_count": 3,
        }
        html = _render_report_email("products", "Product Report", data)
        assert "Total Products" in html
        assert "Low Stock" in html

    def test_unknown_type_no_summary(self) -> None:
        from routes.report_schedules_helpers import _render_report_email

        html = _render_report_email("custom", "Custom Report", {"rows": []})
        # No summary div for unknown types — none of the known summary labels appear
        assert "Total Revenue" not in html
        assert "Total Tickets" not in html
        assert "Total Collected" not in html
        assert "Total Products" not in html
        assert "Low Stock" not in html
