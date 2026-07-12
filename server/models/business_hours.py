"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Business Hours ─────────────────────────────────────────────


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
