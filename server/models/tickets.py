"""Ticket request models."""

from pydantic import Field

from .base import BaseModel


class TicketCreate(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=5000)
    device_type: str = Field(default="", max_length=100)
    device_model: str = Field(default="", max_length=100)
    device_serial: str = Field(default="", max_length=100)
    device_imei: str = Field(default="", max_length=100)
    device_password: str = Field(default="", max_length=100)
    priority: str = Field(default="normal", max_length=50)


class TicketTimerStart(BaseModel):
    user_id: str = Field(default="", max_length=100)


class TicketStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)


class TicketAssign(BaseModel):
    assigned_user_id: str = Field(..., min_length=1, max_length=100)


class TicketNoteCreate(BaseModel):
    author: str = Field(default="", max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    internal: bool = False
