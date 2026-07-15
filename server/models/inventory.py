"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Inventory ───────────────────────────────────────────────────


class InventoryAdjustmentCreate(BaseModel):
    quantity_change: float = Field(...)
    reason: str = Field(default="other", max_length=100)
    reference_id: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=2000)
    user_id: str = Field(default="", max_length=100)


class StockTransferRequest(BaseModel):
    source_product_id: str = Field(..., min_length=1, max_length=100)
    destination_product_id: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., gt=0)
    reference_id: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=2000)
