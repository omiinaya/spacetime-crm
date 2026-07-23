"""DayHours / BusinessHours — time pattern."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestDayHours:
    def test_defaults(self) -> None:
        from models import DayHours

        m = DayHours()
        assert m.enabled is True
        assert m.open == "09:00"
        assert m.close == "18:00"

    def test_valid_times(self) -> None:
        from models import DayHours

        for time_str in ("00:00", "08:30", "12:00", "23:59"):
            m = DayHours(open=time_str, close=time_str)
            assert m.open == time_str

    def test_invalid_time_format(self) -> None:
        from models import DayHours

        with pytest.raises(ValidationError, match="open"):
            DayHours(open="9:00")

    def test_invalid_time_format_no_leading_zero(self) -> None:
        from models import DayHours

        with pytest.raises(ValidationError):
            DayHours(close="9:00")

    def test_invalid_time_no_colon(self) -> None:
        from models import DayHours

        with pytest.raises(ValidationError):
            DayHours(open="0900")


class TestBusinessHoursUpdate:
    def test_defaults(self) -> None:
        from models import BusinessHoursUpdate

        m = BusinessHoursUpdate()
        assert m.monday.enabled is True
        assert m.monday.open == "09:00"
        assert m.saturday.enabled is False
        assert m.sunday.enabled is False
