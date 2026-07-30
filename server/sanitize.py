"""Input sanitization utilities for XSS protection.

Strips HTML tags from string inputs to prevent stored XSS.
Applied automatically via SanitizedModel base class.
"""

import re
from pydantic import BaseModel, model_validator


def strip_html(value: str) -> str:
    """Remove HTML tags from a string value.

    Uses regex to strip anything that looks like an HTML/XML tag.
    Safe for all text fields — preserves the content outside tags.
    """
    if isinstance(value, str):
        return re.sub(r"<[^>]*>", "", value)
    return value


# Fields to skip HTML sanitization — these may contain legitimate
# special characters or are already hashed/opaque.
_SKIP_SANITIZE = {"password", "token", "secret", "smtp_password", "twilio_auth_token"}


class SanitizedModel(BaseModel):
    """Base model that strips HTML tags from all string fields after validation.

    Fields named 'password', 'token', 'secret', 'smtp_password', and
    'twilio_auth_token' are skipped to avoid corrupting opaque values.

    Usage:
        class MyRequest(SanitizedModel):
            name: str = Field(..., max_length=100)
            content: str = Field(default="", max_length=2000)
    """

    @model_validator(mode="after")
    def _strip_html_from_strings(self):
        for field_name in self.__class__.model_fields:
            if field_name in _SKIP_SANITIZE:
                continue
            value = getattr(self, field_name)
            if isinstance(value, str):
                setattr(self, field_name, strip_html(value))
        return self
