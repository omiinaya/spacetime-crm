"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Tickets ─────────────────────────────────────────────────────


class TicketCreate(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=5000)
    device_type: str = Field(default="", max_length=100)
    device_model: str = Field(default="", max_length=100)
    device_serial: str = Field(default="", max_length=100)
    device_imei: str = Field(default="", max_length=100)
    device_password: str = Field(default="", max_length=100)
    priority: str = Field(default="normal", max_length=50)


class TicketTimerStart(BaseModel):
    user_id: str = Field(default="", max_length=100)


class TicketStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)


class TicketAssign(BaseModel):
    assigned_user_id: str = Field(..., min_length=1, max_length=100)


class TicketNoteCreate(BaseModel):
    author: str = Field(default="", max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    internal: bool = False


