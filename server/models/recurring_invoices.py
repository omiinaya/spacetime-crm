"""Recurring invoice request models."""

from pydantic import Field
from .base import BaseModel


class RecurringInvoiceLineItem(BaseModel):
    description: str = Field(default="", max_length=500)
    quantity: float = Field(default=1, ge=0)
    unit_price: float = Field(default=0, ge=0)
    item_type: str = Field(default="service", max_length=100)


class RecurringInvoiceRuleCreate(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    frequency: str = Field(
        ..., pattern=r"^(daily|weekly|biweekly|monthly|quarterly|yearly)$"
    )
    interval_count: int = Field(default=1, ge=1, le=365)
    due_date_days: int = Field(default=30, ge=0, le=365)
    line_items: list[RecurringInvoiceLineItem] = Field(default_factory=list)
    next_generation_date: int = Field(default=0, ge=0)


class RecurringInvoiceRuleUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    frequency: str = Field(
        ..., pattern=r"^(daily|weekly|biweekly|monthly|quarterly|yearly)$"
    )
    interval_count: int = Field(default=1, ge=1, le=365)
    due_date_days: int = Field(default=30, ge=0, le=365)
    line_items: list[RecurringInvoiceLineItem] = Field(default_factory=list)
    next_generation_date: int = Field(default=0, ge=0)
    status: str = Field(default="active", pattern=r"^(active|paused|cancelled)$")
