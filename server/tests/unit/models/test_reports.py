"""ScheduledReport — regex pattern validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestScheduledReportCreate:
    def test_valid(self) -> None:
        from models import ScheduledReportCreate

        m = ScheduledReportCreate(
            name="Weekly Revenue Report",
            report_type="revenue",
            schedule_frequency="weekly",
            recipients=["admin@example.com"],
        )
        assert m.name == "Weekly Revenue Report"
        assert m.report_type == "revenue"
        assert m.schedule_frequency == "weekly"
        assert m.recipients == ["admin@example.com"]

    def test_invalid_report_type(self) -> None:
        from models import ScheduledReportCreate

        with pytest.raises(ValidationError, match="report_type"):
            ScheduledReportCreate(
                name="Bad Report",
                report_type="sales",
                schedule_frequency="weekly",
                recipients=["admin@example.com"],
            )

    def test_invalid_schedule_frequency(self) -> None:
        from models import ScheduledReportCreate

        with pytest.raises(ValidationError, match="schedule_frequency"):
            ScheduledReportCreate(
                name="Bad Report",
                report_type="revenue",
                schedule_frequency="annually",
                recipients=["admin@example.com"],
            )

    def test_valid_report_types(self) -> None:
        from models import ScheduledReportCreate

        for rtype in (
            "revenue",
            "tickets",
            "invoices",
            "appointments",
            "tech_productivity",
            "customers",
        ):
            m = ScheduledReportCreate(
                name=f"{rtype} Report",
                report_type=rtype,
                schedule_frequency="monthly",
                recipients=["a@b.com"],
            )
            assert m.report_type == rtype

    def test_valid_frequencies(self) -> None:
        from models import ScheduledReportCreate

        for freq in ("daily", "weekly", "monthly"):
            m = ScheduledReportCreate(
                name="Report",
                report_type="revenue",
                schedule_frequency=freq,
                recipients=["a@b.com"],
            )
            assert m.schedule_frequency == freq

    def test_empty_recipients_raises(self) -> None:
        """recipients has min_length=1."""
        from models import ScheduledReportCreate

        with pytest.raises(ValidationError):
            ScheduledReportCreate(
                name="Report",
                report_type="revenue",
                schedule_frequency="daily",
                recipients=[],
            )

    def test_name_too_long(self) -> None:
        from models import ScheduledReportCreate

        with pytest.raises(ValidationError):
            ScheduledReportCreate(
                name="x" * 201,
                report_type="revenue",
                schedule_frequency="daily",
                recipients=["a@b.com"],
            )

    def test_missing_name_raises(self) -> None:
        from models import ScheduledReportCreate

        with pytest.raises(ValidationError):
            ScheduledReportCreate(
                report_type="revenue",
                schedule_frequency="daily",
                recipients=["a@b.com"],
            )


class TestScheduledReportUpdate:
    def test_valid_enabled_default(self) -> None:
        from models import ScheduledReportUpdate

        m = ScheduledReportUpdate(
            name="Updated Report",
            report_type="tickets",
            schedule_frequency="weekly",
            recipients=["admin@example.com"],
        )
        assert m.enabled is True

    def test_enabled_false(self) -> None:
        from models import ScheduledReportUpdate

        m = ScheduledReportUpdate(
            name="Report",
            report_type="tickets",
            schedule_frequency="weekly",
            recipients=["admin@example.com"],
            enabled=False,
        )
        assert m.enabled is False
