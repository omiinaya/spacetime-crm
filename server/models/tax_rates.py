"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Tax Rates ───────────────────────────────────────────────────


class TaxRateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    rate: float = Field(..., ge=0, le=100)
    is_default: bool = False


class TaxRateUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    rate: float = Field(..., ge=0, le=100)
    is_default: bool = False


