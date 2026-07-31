"""Appointment request models."""

from pydantic import Field

from .base import BaseModel


class AppointmentCreate(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=100)
    ticket_id: str = Field(default="", max_length=100)
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=2000)
    start_time: int = Field(..., ge=0)
    end_time: int = Field(..., ge=0)
    all_day: bool = False
    series_id: str = Field(default="", max_length=100)
    recurrence_rule: str = Field(default="", max_length=50)
    color: str = Field(default="", max_length=20)
    assigned_user_id: str = Field(default="", max_length=100)


class AppointmentStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)


class AppointmentRecurrence(BaseModel):
    recurrence_rule: str = Field(..., max_length=50)


class GenerateNextOccurrence(BaseModel):
    series_id: str = Field(..., min_length=1, max_length=100)
