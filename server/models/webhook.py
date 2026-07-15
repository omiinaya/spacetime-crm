"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Webhook ─────────────────────────────────────────────────────


class WebhookSubscriptionCreate(BaseModel):
    url: str = Field(..., min_length=5, max_length=2000)
    events: str = Field(..., min_length=1)
    secret: str = Field(default="", max_length=500)


class WebhookSubscriptionUpdate(BaseModel):
    url: str = Field(..., min_length=5, max_length=2000)
    events: str = Field(..., min_length=1)
    secret: str = Field(default="", max_length=500)
    active: bool = True
