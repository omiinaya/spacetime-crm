"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Custom Fields ───────────────────────────────────────────────


class CustomFieldDefinitionCreate(BaseModel):
    id: str = Field(default="", max_length=100)
    entity_type: str = Field(..., pattern=r"^(customer|ticket|invoice|product)$")
    label: str = Field(..., min_length=1, max_length=255)
    field_type: str = Field(..., pattern=r"^(text|number|date|select|multiselect|checkbox|textarea)$")
    options: list[str] = Field(default=[])
    sort_order: int = Field(default=0, ge=0)
    required: bool = False
    active: bool = True


class CustomFieldValuesUpdate(BaseModel):
    values: dict[str, str | int | float | bool | list[str]] = {}
