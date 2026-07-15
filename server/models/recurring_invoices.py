"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Recurring Invoices ─────────────────────────────────────────


class RecurringInvoiceLineItem(BaseModel):
    description: str = Field(default="", max_length=500)
    quantity: float = Field(default=1, ge=0)
    unit_price: float = Field(default=0, ge=0)
    item_type: str = Field(default="service", max_length=100)


class RecurringInvoiceRuleCreate(BaseModel):
    currency: str = Field(default="USD", max_length=3)
    customer_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    frequency: str = Field(..., pattern=r"^(daily|weekly|biweekly|monthly|quarterly|yearly)$")
    interval_count: int = Field(default=1, ge=1, le=365)
    due_date_days: int = Field(default=30, ge=0, le=365)
    line_items: list[RecurringInvoiceLineItem] = Field(default_factory=list)
    next_generation_date: int = Field(default=0, ge=0)


class RecurringInvoiceRuleUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    frequency: str = Field(..., pattern=r"^(daily|weekly|biweekly|monthly|quarterly|yearly)$")
    interval_count: int = Field(default=1, ge=1, le=365)
    due_date_days: int = Field(default=30, ge=0, le=365)
    line_items: list[RecurringInvoiceLineItem] = Field(default_factory=list)
    next_generation_date: int = Field(default=0, ge=0)
    status: str = Field(default="active", pattern=r"^(active|paused|cancelled)$")
    currency: str = Field(default="USD", max_length=3)
