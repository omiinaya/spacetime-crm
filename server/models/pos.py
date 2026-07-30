"""POS / Counter sale request models."""

from pydantic import Field
from .base import BaseModel


class POSCreate(BaseModel):
    customer_id: str = Field(default="", max_length=100)
    customer_name: str = Field(default="Walk-in", max_length=255)
    payment_method: str = Field(default="cash", pattern=r"^(cash|card|invoice)$")
    amount_tendered: float = Field(default=0, ge=0)
    tax_rate: float = Field(default=0, ge=0, le=100)
    discount_amount: float = Field(default=0, ge=0)
    currency: str = Field(default="USD", max_length=10)


class POSAddItem(BaseModel):
    sale_id: str = Field(..., min_length=1, max_length=100)
    product_id: str = Field(..., min_length=1, max_length=100)
    product_name: str = Field(..., max_length=255)
    sku: str = Field(default="", max_length=100)
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
