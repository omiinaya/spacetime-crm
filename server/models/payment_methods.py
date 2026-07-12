"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Payment Methods ────────────────────────────────────────────


class SavePaymentMethodRequest(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=100)
    stripe_payment_method_id: str = Field(..., min_length=1, max_length=255)
    brand: str = Field(..., max_length=50)
    last4: str = Field(..., pattern=r"^\d{4}$")
    exp_month: int = Field(..., ge=1, le=12)
    exp_year: int = Field(..., ge=2020, le=2100)


class SetDefaultPaymentMethodRequest(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=100)


class PortalPayWithSavedCard(BaseModel):
    invoice_id: str = Field(..., min_length=1)
    payment_method_id: str = Field(..., min_length=1)


