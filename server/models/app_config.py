"""Pydantic models for app-level configuration (revenue target, reminders)."""

from pydantic import Field

from .base import BaseModel


class AppConfigUpdate(BaseModel):
    """App-level config (revenue target, reminder schedule)."""

    revenue_target: float | None = Field(default=None, ge=0)
    reminder_interval_days: int | None = Field(default=None, ge=1, le=365)
