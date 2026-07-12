"""Unit tests for report_engine module (extracted from report_schedules.py)."""

from datetime import datetime, timezone
from report_engine import render_report_email, calc_next_run


class TestCalcNextRun:
    def test_daily_same_day_later(self):
        """If scheduled time is later today, return today."""
        dt = datetime(2024, 1, 15, 6, 0, 0, tzinfo=timezone.utc)
        from_ms = int(dt.timestamp() * 1000)
        result = calc_next_run("daily", {"hour": 8, "minute": 0}, from_ms)
        result_dt = datetime.fromtimestamp(result / 1000, tz=timezone.utc)
        assert result_dt.day == 15
        assert result_dt.hour == 8
        assert result_dt.minute == 0

    def test_daily_next_day(self):
        """If scheduled time already passed today, return tomorrow."""
        dt = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        from_ms = int(dt.timestamp() * 1000)
        result = calc_next_run("daily", {"hour": 8, "minute": 0}, from_ms)
        result_dt = datetime.fromtimestamp(result / 1000, tz=timezone.utc)
        assert result_dt.day == 16
        assert result_dt.hour == 8
        assert result_dt.minute == 0

    def test_weekly_monday(self):
        """If today is Monday (0) and scheduled hour not passed, return today."""
        dt = datetime(2024, 1, 1, 6, 0, 0, tzinfo=timezone.utc)
        from_ms = int(dt.timestamp() * 1000)
        result = calc_next_run("weekly", {"day_of_week": 0, "hour": 8, "minute": 0}, from_ms)
        result_dt = datetime.fromtimestamp(result / 1000, tz=timezone.utc)
        assert result_dt.day == 1
        assert result_dt.hour == 8

    def test_weekly_next_week(self):
        """If scheduled day already passed this week, return next week."""
        dt = datetime(2024, 1, 2, 10, 0, 0, tzinfo=timezone.utc)
        from_ms = int(dt.timestamp() * 1000)
        result = calc_next_run("weekly", {"day_of_week": 1, "hour": 8, "minute": 0}, from_ms)
        result_dt = datetime.fromtimestamp(result / 1000, tz=timezone.utc)
        assert result_dt.day == 9
        assert result_dt.hour == 8

    def test_monthly_same_day(self):
        dt = datetime(2024, 1, 15, 6, 0, 0, tzinfo=timezone.utc)
        from_ms = int(dt.timestamp() * 1000)
        result = calc_next_run("monthly", {"day_of_month": 15, "hour": 8, "minute": 0}, from_ms)
        result_dt = datetime.fromtimestamp(result / 1000, tz=timezone.utc)
        assert result_dt.month == 1
        assert result_dt.day == 15
        assert result_dt.hour == 8

    def test_monthly_next_month(self):
        dt = datetime(2024, 1, 16, 6, 0, 0, tzinfo=timezone.utc)
        from_ms = int(dt.timestamp() * 1000)
        result = calc_next_run("monthly", {"day_of_month": 15, "hour": 8, "minute": 0}, from_ms)
        result_dt = datetime.fromtimestamp(result / 1000, tz=timezone.utc)
        assert result_dt.month == 2
        assert result_dt.day == 15
        assert result_dt.hour == 8

    def test_monthly_dec_to_jan(self):
        dt = datetime(2024, 12, 20, 6, 0, 0, tzinfo=timezone.utc)
        from_ms = int(dt.timestamp() * 1000)
        result = calc_next_run("monthly", {"day_of_month": 15, "hour": 8, "minute": 0}, from_ms)
        result_dt = datetime.fromtimestamp(result / 1000, tz=timezone.utc)
        assert result_dt.year == 2025
        assert result_dt.month == 1
        assert result_dt.day == 15


class TestRenderReportEmail:
    def test_simple_metrics(self):
        data = {
            "title": "Revenue Report",
            "metrics": [
                {"label": "Total Revenue", "value": "$10,000"},
                {"label": "Invoices Sent", "value": 42},
            ],
        }
        html = render_report_email("revenue", "Test Report", data)
        assert "Total Revenue" in html
        assert "$10,000" in html
        assert "42" in html
        assert "SpacetimeCRM" in html

    def test_with_chart(self):
        data = {
            "title": "Revenue by Month",
            "metrics": [{"label": "Total", "value": "$5,000"}],
            "chart_label": "Monthly Revenue",
            "chart": [
                {"label": "Jan", "value": 1000},
                {"label": "Feb", "value": 2000},
            ],
        }
        html = render_report_email("revenue", "Chart Report", data)
        assert "Monthly Revenue" in html
        assert "Jan" in html
        assert "Feb" in html

    def test_with_chart2(self):
        data = {
            "title": "Dual Chart",
            "metrics": [{"label": "Total", "value": "$5,000"}],
            "chart_label": "Primary",
            "chart": [{"label": "A", "value": 10}],
            "chart2_label": "Secondary",
            "chart2": [{"label": "X", "value": 5, "extra": "Note"}],
        }
        html = render_report_email("revenue", "Dual", data)
        assert "Primary" in html
        assert "Secondary" in html
        assert "Note" in html

    def test_empty_chart(self):
        data = {"title": "Empty", "metrics": []}
        html = render_report_email("test", "Empty Report", data)
        assert "Empty" in html
