"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── User ────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=255)
    role: str = Field(default="tech", pattern=r"^(admin|tech|front_desk)$")


class UserUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=255)
    role: str = Field(..., pattern=r"^(admin|tech|front_desk)$")
    active: bool = True


class UserSettingsUpdate(BaseModel):
    theme: str = Field(default="light", pattern=r"^(light|dark)$")
    default_ticket_status: str = Field(default="new", max_length=50)
