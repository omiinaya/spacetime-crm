"""Auth request models — login, password management, 2FA/TOTP, PIN."""

from pydantic import Field

from .base import BaseModel


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class SetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=4, max_length=255)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)


class ResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=6, max_length=255)
    token: str = Field(..., min_length=1)


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
