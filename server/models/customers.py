"""Customer request models."""

from pydantic import Field

from .base import BaseModel


class CustomerCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(default="", max_length=255)
    phone: str = Field(default="", max_length=50)
    mobile: str = Field(default="", max_length=50)
    company: str = Field(default="", max_length=255)
    address_line1: str = Field(default="", max_length=255)
    address_line2: str = Field(default="", max_length=255)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=50)
    zip: str = Field(default="", max_length=20)
    notes: str = Field(default="", max_length=2000)
    tags: str = Field(default="", max_length=500)


class CustomerUpdate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(default="", max_length=255)
    phone: str = Field(default="", max_length=50)
    mobile: str = Field(default="", max_length=50)
    company: str = Field(default="", max_length=255)
    address_line1: str = Field(default="", max_length=255)
    address_line2: str = Field(default="", max_length=255)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=50)
    zip: str = Field(default="", max_length=20)
    notes: str = Field(default="", max_length=2000)
    tags: str = Field(default="", max_length=500)
