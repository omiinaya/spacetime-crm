"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── Mail/SMS Settings ───────────────────────────────────────────


class MailSettingsUpdate(BaseModel):
    smtp_host: str = Field(default="", max_length=255)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str = Field(default="", max_length=255)
    smtp_password: str = Field(default="", max_length=500)
    smtp_from_email: str = Field(default="", max_length=255)
    smtp_from_name: str = Field(default="", max_length=100)
    smtp_tls: bool = True
    enabled: bool = False


class SMSSettingsUpdate(BaseModel):
    twilio_account_sid: str = Field(default="", max_length=255)
    twilio_auth_token: str = Field(default="", max_length=500)
    twilio_from_number: str = Field(default="", max_length=20)
    enabled: bool = False


