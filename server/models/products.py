"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Products ────────────────────────────────────────────────────


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(default="", max_length=100)
    barcode: str = Field(default="", max_length=100)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="", max_length=100)
    price: float = Field(default=0, ge=0)
    cost: float = Field(default=0, ge=0)
    quantity_on_hand: float = Field(default=0, ge=0)
    min_stock: float = Field(default=0, ge=0)
    location: str = Field(default="", max_length=255)
    active: bool = True


class ProductQuantityUpdate(BaseModel):
    quantity_on_hand: float = Field(..., ge=0)
