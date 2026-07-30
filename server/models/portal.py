"""Customer portal request models."""

from pydantic import Field
from .base import BaseModel


class PortalLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class PortalNoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class PortalPaymentCreate(BaseModel):
    invoice_id: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    method: str = Field(default="card", max_length=50)
    reference: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=2000)


class PortalSetPassword(BaseModel):
    password: str = Field(..., min_length=6, max_length=255)


class PortalCheckoutSessionCreate(BaseModel):
    invoice_id: str = Field(..., min_length=1)
