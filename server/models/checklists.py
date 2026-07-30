"""Checklist template request models."""

from pydantic import Field
from .base import BaseModel


class ChecklistTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    items: list[dict] = []


class ChecklistTemplateUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    items: list[dict] = []


class ChecklistApply(BaseModel):
    template_id: str = Field(..., min_length=1)


class ChecklistToggle(BaseModel):
    completed: bool = False
