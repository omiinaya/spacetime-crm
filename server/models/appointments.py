"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Appointments ────────────────────────────────────────────────


class AppointmentCreate(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=100)
    ticket_id: str = Field(default="", max_length=100)
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=2000)
    start_time: int = Field(..., ge=0)
    end_time: int = Field(..., ge=0)
    all_day: bool = False
    series_id: str = Field(default="", max_length=100)
    recurrence_rule: str = Field(default="", max_length=50)
    color: str = Field(default="", max_length=20)


class AppointmentStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)


class AppointmentRecurrence(BaseModel):
    recurrence_rule: str = Field(..., max_length=50)


class GenerateNextOccurrence(BaseModel):
    series_id: str = Field(..., min_length=1, max_length=100)
