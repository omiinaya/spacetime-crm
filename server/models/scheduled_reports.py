"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Scheduled Reports ──────────────────────────────────────────


class ScheduledReportCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    report_type: str = Field(..., pattern=r"^(revenue|tickets|invoices|appointments|tech_productivity|customers)$")
    schedule_frequency: str = Field(..., pattern=r"^(daily|weekly|monthly)$")
    schedule_config: dict = Field(default_factory=dict)
    recipients: list[str] = Field(..., min_length=1)
    filters: dict = Field(default_factory=dict)


class ScheduledReportUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    report_type: str = Field(..., pattern=r"^(revenue|tickets|invoices|appointments|tech_productivity|customers)$")
    schedule_frequency: str = Field(..., pattern=r"^(daily|weekly|monthly)$")
    schedule_config: dict = Field(default_factory=dict)
    recipients: list[str] = Field(..., min_length=1)
    filters: dict = Field(default_factory=dict)
    enabled: bool = True
