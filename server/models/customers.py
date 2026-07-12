"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Customers ───────────────────────────────────────────────────


class CustomerCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(default="", max_length=255)
    phone: str = Field(default="", max_length=50)
    mobile: str = Field(default="", max_length=50)
    company: str = Field(default="", max_length=255)
    address_line1: str = Field(default="", max_length=255)
    address_line2: str = Field(default="", max_length=255)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=50)
    zip: str = Field(default="", max_length=20)
    notes: str = Field(default="", max_length=2000)
    tags: str = Field(default="", max_length=500)


class CustomerUpdate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(default="", max_length=255)
    phone: str = Field(default="", max_length=50)
    mobile: str = Field(default="", max_length=50)
    company: str = Field(default="", max_length=255)
    address_line1: str = Field(default="", max_length=255)
    address_line2: str = Field(default="", max_length=255)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=50)
    zip: str = Field(default="", max_length=20)
    notes: str = Field(default="", max_length=2000)
    tags: str = Field(default="", max_length=500)


