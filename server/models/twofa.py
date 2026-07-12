"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel

# ─── 2FA / TOTP ─────────────────────────────────────────────────


class Setup2FARequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class CompleteLoginRequest(BaseModel):
    temp_token: str = Field(..., min_length=1)
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class Disable2FARequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class SetPinRequest(BaseModel):
    pin: str = Field(default="", min_length=0, max_length=10, pattern=r"^\d{0,10}$")


class PosLoginRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=100)
    pin: str = Field(..., min_length=4, max_length=10, pattern=r"^\d{4,10}$")


