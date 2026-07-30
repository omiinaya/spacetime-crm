"""Business hours request models."""

from pydantic import Field

from .base import BaseModel


class DayHours(BaseModel):
    enabled: bool = True
    open: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    close: str = Field(default="18:00", pattern=r"^\d{2}:\d{2}$")


class BusinessHoursUpdate(BaseModel):
    monday: DayHours = DayHours()
    tuesday: DayHours = DayHours()
    wednesday: DayHours = DayHours()
    thursday: DayHours = DayHours()
    friday: DayHours = DayHours()
    saturday: DayHours = DayHours(enabled=False, open="10:00", close="14:00")
    sunday: DayHours = DayHours(enabled=False, open="10:00", close="14:00")
