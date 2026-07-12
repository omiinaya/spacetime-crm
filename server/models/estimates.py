"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Estimates ───────────────────────────────────────────────────


class EstimateCreate(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=100)
    ticket_id: str = Field(default="", max_length=100)
    notes: str = Field(default="", max_length=2000)
    expires_at: int = Field(default=0, ge=0)
    currency: str = Field(default="USD", max_length=3)
    tax_rate: float = Field(default=0, ge=0, le=100)
    discount_amount: float = Field(default=0, ge=0)


class EstimateStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)


class EstimateLineItemCreate(BaseModel):
    item_type: str = Field(default="service", max_length=100)
    description: str = Field(default="", max_length=500)
    quantity: float = Field(default=1, ge=0)
    unit_price: float = Field(default=0, ge=0)


