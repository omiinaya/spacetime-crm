"""Invoice and payment request models."""

from pydantic import Field
from .base import BaseModel


class InvoiceCreate(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=100)
    ticket_id: str = Field(default="", max_length=100)
    notes: str = Field(default="", max_length=2000)
    terms: str = Field(default="", max_length=500)
    due_date: int = Field(default=0, ge=0)
    currency: str = Field(default="USD", max_length=3)
    discount_amount: float = Field(default=0, ge=0)
    discount_percent: float = Field(default=0, ge=0, le=100)


class InvoiceStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)


class InvoiceLineItemCreate(BaseModel):
    item_type: str = Field(default="service", max_length=100)
    description: str = Field(default="", max_length=500)
    quantity: float = Field(default=1, ge=0)
    unit_price: float = Field(default=0, ge=0)


class InvoiceTaxRateUpdate(BaseModel):
    tax_rate: float = Field(..., ge=0, le=100)


class BulkInvoiceStatusUpdate(BaseModel):
    invoice_ids: list[str] = Field(..., min_length=1, max_length=500)
    status: str = Field(..., min_length=1, max_length=50)


class BulkInvoiceEdit(BaseModel):
    invoice_ids: list[str] = Field(..., min_length=1, max_length=500)
    terms: str = Field(default="", max_length=2000)
    notes: str = Field(default="", max_length=2000)


class PaymentCreate(BaseModel):
    invoice_id: str = Field(..., min_length=1, max_length=100)
    customer_id: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    method: str = Field(default="cash", max_length=50)
    reference: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=2000)
    currency: str = Field(default="USD", max_length=3)
