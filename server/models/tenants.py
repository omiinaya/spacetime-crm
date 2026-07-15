"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Tenants ─────────────────────────────────────────────────────


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(default="", max_length=255)


class TenantUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(default="", max_length=255)
    logo_url: str = Field(default="", max_length=1000)
    settings: str = Field(default="{}", max_length=10000)


class TenantMemberAdd(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="user", max_length=50)


class TenantMemberRoleUpdate(BaseModel):
    role: str = Field(..., min_length=1, max_length=50)
