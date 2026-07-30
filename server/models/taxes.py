"""Tax rate request models."""

from pydantic import Field
from .base import BaseModel


class TaxRateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    rate: float = Field(..., ge=0, le=100)
    is_default: bool = False


class TaxRateUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    rate: float = Field(..., ge=0, le=100)
    is_default: bool = False
