"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Portal ──────────────────────────────────────────────────────


class PortalLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class PortalNoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class PortalPaymentCreate(BaseModel):
    invoice_id: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    method: str = Field(default="card", max_length=50)
    reference: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=2000)


class PortalSetPassword(BaseModel):
    password: str = Field(..., min_length=6, max_length=255)


class PortalCheckoutSessionCreate(BaseModel):
    invoice_id: str = Field(..., min_length=1)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)


class ResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=6, max_length=255)
    token: str = Field(..., min_length=1)


class TenantMigrate(BaseModel):
    name: str = Field(default="Default", max_length=255)
    slug: str = Field(default="", max_length=255)
