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

    def test_enabled_false(self) -> None:
        from models import DayHours

        m = DayHours(enabled=False, open="10:00", close="14:00")
        assert m.enabled is False
        assert m.open == "10:00"
        assert m.close == "14:00"

    def test_custom_open_close(self) -> None:
        from models import DayHours

        m = DayHours(open="07:30", close="22:45")
        assert m.open == "07:30"
        assert m.close == "22:45"

    def test_midnight_times(self) -> None:
        from models import DayHours

        m = DayHours(open="00:00", close="23:59")
        assert m.open == "00:00"
        assert m.close == "23:59"

    def test_close_before_open_allowed(self) -> None:
        """Validation only checks format, not logical ordering."""
        from models import DayHours

        m = DayHours(open="22:00", close="06:00")
        assert m.open == "22:00"
        assert m.close == "06:00"


class TestBusinessHoursUpdate:
    def test_defaults(self) -> None:
        from models import BusinessHoursUpdate

        m = BusinessHoursUpdate()
        assert m.monday.enabled is True
        assert m.monday.open == "09:00"
        assert m.saturday.enabled is False
        assert m.sunday.enabled is False

    def test_weekday_defaults(self) -> None:
        from models import BusinessHoursUpdate

        m = BusinessHoursUpdate()
        for day in ("monday", "tuesday", "wednesday", "thursday", "friday"):
            d = getattr(m, day)
            assert d.enabled is True
            assert d.open == "09:00"
            assert d.close == "18:00"

    def test_weekend_defaults(self) -> None:
        from models import BusinessHoursUpdate

        m = BusinessHoursUpdate()
        for day in ("saturday", "sunday"):
            d = getattr(m, day)
            assert d.enabled is False
            assert d.open == "10:00"
            assert d.close == "14:00"

    def test_custom_hours(self) -> None:
        from models import BusinessHoursUpdate, DayHours

        m = BusinessHoursUpdate(
            monday=DayHours(enabled=True, open="08:00", close="17:00"),
            tuesday=DayHours(enabled=False, open="10:00", close="14:00"),
        )
        assert m.monday.open == "08:00"
        assert m.monday.close == "17:00"
        assert m.tuesday.enabled is False
        # Other days keep defaults
        assert m.wednesday.enabled is True
        assert m.wednesday.open == "09:00"

    def test_all_weekdays_enabled(self) -> None:
        from models import BusinessHoursUpdate, DayHours

        m = BusinessHoursUpdate(
            monday=DayHours(enabled=True, open="07:00", close="19:00"),
            tuesday=DayHours(enabled=True, open="07:00", close="19:00"),
            wednesday=DayHours(enabled=True, open="07:00", close="19:00"),
            thursday=DayHours(enabled=True, open="07:00", close="19:00"),
            friday=DayHours(enabled=True, open="07:00", close="19:00"),
            saturday=DayHours(enabled=True, open="08:00", close="16:00"),
            sunday=DayHours(enabled=True, open="08:00", close="16:00"),
        )
        for day in (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ):
            assert getattr(m, day).enabled is True
