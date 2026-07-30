"""Purchase order request models."""

from pydantic import Field
from .base import BaseModel


class PurchaseOrderCreate(BaseModel):
    vendor_name: str = Field(..., min_length=1, max_length=255)
    notes: str = Field(default="", max_length=2000)
    currency: str = Field(default="USD", max_length=3)
    shipping_cost: float = Field(default=0, ge=0)


class PurchaseOrderStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)


class POLineItemCreate(BaseModel):
    product_id: str = Field(default="")
    description: str = Field(default="", max_length=500)
    quantity: float = Field(default=1, ge=0)
    unit_price: float = Field(default=0, ge=0)


class POReceiveItem(BaseModel):
    received_quantity: float = Field(..., ge=0)
    items: list[dict] = []


class POApprovalAction(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
