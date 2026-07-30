"""Custom field request models."""

from pydantic import Field

from .base import BaseModel


class CustomFieldDefinitionCreate(BaseModel):
    id: str = Field(default="", max_length=100)
    entity_type: str = Field(..., pattern=r"^(customer|ticket|invoice|product)$")
    label: str = Field(..., min_length=1, max_length=255)
    field_type: str = Field(
        ..., pattern=r"^(text|number|date|select|multiselect|checkbox|textarea)$"
    )
    options: list[str] = Field(default=[])
    sort_order: int = Field(default=0, ge=0)
    required: bool = False
    active: bool = True


class CustomFieldValuesUpdate(BaseModel):
    values: dict[str, str | int | float | bool | list[str]] = Field(default_factory=dict)
