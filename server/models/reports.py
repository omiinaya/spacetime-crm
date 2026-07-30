"""Scheduled report request models."""

from pydantic import Field
from .base import BaseModel


class ScheduledReportCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    report_type: str = Field(
        ...,
        pattern=r"^(revenue|tickets|invoices|appointments|tech_productivity|customers)$",
    )
    schedule_frequency: str = Field(..., pattern=r"^(daily|weekly|monthly)$")
    schedule_config: dict = Field(default_factory=dict)
    recipients: list[str] = Field(..., min_length=1)
    filters: dict = Field(default_factory=dict)


class ScheduledReportUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    report_type: str = Field(
        ...,
        pattern=r"^(revenue|tickets|invoices|appointments|tech_productivity|customers)$",
    )
    schedule_frequency: str = Field(..., pattern=r"^(daily|weekly|monthly)$")
    schedule_config: dict = Field(default_factory=dict)
    recipients: list[str] = Field(..., min_length=1)
    filters: dict = Field(default_factory=dict)
    enabled: bool = True
