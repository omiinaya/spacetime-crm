"""Webhook subscription and mail/SMS settings request models."""

from pydantic import Field
from .base import BaseModel


class WebhookSubscriptionCreate(BaseModel):
    url: str = Field(..., min_length=5, max_length=2000)
    events: str = Field(..., min_length=1)
    secret: str = Field(default="", max_length=500)


class WebhookSubscriptionUpdate(BaseModel):
    url: str = Field(..., min_length=5, max_length=2000)
    events: str = Field(..., min_length=1)
    secret: str = Field(default="", max_length=500)
    active: bool = True


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
