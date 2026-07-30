"""User request models."""

from pydantic import Field

from .base import BaseModel


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=255)
    role: str = Field(default="tech", pattern=r"^(admin|tech|front_desk)$")


class UserUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=255)
    role: str = Field(..., pattern=r"^(admin|tech|front_desk)$")
    active: bool = True


class UserSettingsUpdate(BaseModel):
    theme: str = Field(default="light", pattern=r"^(light|dark)$")
    default_ticket_status: str = Field(default="new", max_length=50)
