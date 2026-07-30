"""Payment method request models — saved cards for portal customers."""

from pydantic import Field

from .base import BaseModel


class SavePaymentMethodRequest(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=100)
    stripe_payment_method_id: str = Field(..., min_length=1, max_length=255)
    brand: str = Field(..., max_length=50)
    last4: str = Field(..., pattern=r"^\d{4}$")
    exp_month: int = Field(..., ge=1, le=12)
    exp_year: int = Field(..., ge=2020, le=2100)


class SetDefaultPaymentMethodRequest(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=100)


class PortalPayWithSavedCard(BaseModel):
    invoice_id: str = Field(..., min_length=1)
    payment_method_id: str = Field(..., min_length=1)
