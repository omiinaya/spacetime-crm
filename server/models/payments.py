"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Payments ────────────────────────────────────────────────────


class PaymentCreate(BaseModel):
    invoice_id: str = Field(..., min_length=1, max_length=100)
    customer_id: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    method: str = Field(default="cash", max_length=50)
    reference: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=2000)
    currency: str = Field(default="USD", max_length=3)
