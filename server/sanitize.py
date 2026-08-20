"""Input sanitization utilities for XSS protection.

Strips HTML tags from string inputs to prevent stored XSS.
Applied automatically via SanitizedModel base class.

Uses an allowlist approach (bleach.clean): instead of a fragile regex
that only matches well-formed, closed tags, bleach parses the HTML,
drops anything not on the allowlist (including unclosed/malformed tags
like '<svg onload=alert(1)'), and escapes the remainder. This closes the
regex-bypass stored-XSS vector.
"""
import bleach
from pydantic import BaseModel, model_validator


# Allowlist: NO tags, NO attributes, NO protocols.
# Text is preserved but every HTML construct is stripped/escaped, which is
# the safe behavior for all user-facing text fields (ticket titles, notes,
# customer names, etc.).
_ALLOWED_TAGS: list[str] = []
_ALLOWED_ATTRIBUTES: dict[str, list[str]] = {}
_ALLOWED_PROTOCOLS: list[str] = ["http", "https", "mailto"]


def strip_html(value: str) -> str:
    """Remove HTML tags from a string value, safely.

    Uses bleach's allowlist-based sanitizer instead of a regex, so malformed
    or unclosed tags (e.g. '<svg onload=alert(1)') are dropped rather than
    passed through unchanged. Safe for all text fields — preserves the text
    content while removing every tag/attribute/protocol not explicitly
    allowed (none are, here).
    """
    if not isinstance(value, str):
        return value
    return bleach.clean(
        value,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )


# Fields to skip HTML sanitization — these may contain legitimate
# special characters or are already hashed/opaque.
_SKIP_SANITIZE = {"password", "token", "secret", "smtp_password", "twilio_auth_token"}


class SanitizedModel(BaseModel):
    """Base model that sanitizes HTML from all string fields after validation.

    Every string field is run through ``strip_html`` (bleach allowlist) after
    Pydantic validation, so stored input is safe to render in HTML/email
    templates. Fields named 'password', 'token', 'secret', 'smtp_password',
    and 'twilio_auth_token' are skipped to avoid corrupting opaque values.

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
