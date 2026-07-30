"""Product and inventory request models."""

from pydantic import Field

from .base import BaseModel


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
    reorder_quantity: float = Field(default=0, ge=0)
    location: str = Field(default="", max_length=255)
    active: bool = True


class ProductQuantityUpdate(BaseModel):
    quantity_on_hand: float = Field(..., ge=0)


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
