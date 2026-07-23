"""Appointment models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestAppointmentCreate:
    def test_valid(self) -> None:
        from models import AppointmentCreate

        m = AppointmentCreate(
            customer_id="c-001",
            title="Fix laptop",
            start_time=1700000000,
            end_time=1700003600,
        )
        assert m.title == "Fix laptop"
        assert m.all_day is False

    def test_all_day_default(self) -> None:
        from models import AppointmentCreate

        m = AppointmentCreate(
            customer_id="c-001",
            title="All day event",
            start_time=1700000000,
            end_time=1700003600,
        )
        assert m.all_day is False

    def test_start_time_negative(self) -> None:
        from models import AppointmentCreate

        with pytest.raises(ValidationError):
            AppointmentCreate(
                customer_id="c-001",
                title="Test",
                start_time=-1,
                end_time=100,
            )

    def test_end_time_negative(self) -> None:
        from models import AppointmentCreate

        with pytest.raises(ValidationError):
            AppointmentCreate(
                customer_id="c-001",
                title="Test",
                start_time=100,
                end_time=-1,
            )

    def test_title_too_long(self) -> None:
        from models import AppointmentCreate

        with pytest.raises(ValidationError):
            AppointmentCreate(
                customer_id="c-001",
                title="x" * 501,
                start_time=100,
                end_time=200,
            )
