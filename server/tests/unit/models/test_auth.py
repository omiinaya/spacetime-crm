"""Auth models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestLoginRequest:
    def test_valid(self) -> None:
        from models import LoginRequest

        m = LoginRequest(email="user@example.com", password="secret123")
        assert m.email == "user@example.com"
        assert m.password == "secret123"

    def test_missing_email_raises(self) -> None:
        from models import LoginRequest

        with pytest.raises(ValidationError, match="email"):
            LoginRequest(password="secret123")

    def test_missing_password_raises(self) -> None:
        from models import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com")

    def test_email_too_short(self) -> None:
        from models import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(email="ab", password="ok")

    def test_email_too_long(self) -> None:
        from models import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(email="a" * 256, password="ok")

    def test_password_too_long(self) -> None:
        from models import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com", password="x" * 256)


class TestSetPasswordRequest:
    def test_valid(self) -> None:
        from models import SetPasswordRequest

        m = SetPasswordRequest(password="abc12345")
        assert m.password == "abc12345"

    def test_password_too_short(self) -> None:
        from models import SetPasswordRequest

        with pytest.raises(ValidationError):
            SetPasswordRequest(password="abc")

    def test_password_too_long(self) -> None:
        from models import SetPasswordRequest

        with pytest.raises(ValidationError):
            SetPasswordRequest(password="x" * 256)

    def test_empty_password_raises(self) -> None:
        from models import SetPasswordRequest

        with pytest.raises(ValidationError):
            SetPasswordRequest(password="")

    def test_missing_password_raises(self) -> None:
        from models import SetPasswordRequest

        with pytest.raises(ValidationError):
            SetPasswordRequest()


class TestPortalSetPassword:
    def test_valid(self) -> None:
        from models import PortalSetPassword

        m = PortalSetPassword(password="abcdefg")
        assert m.password == "abcdefg"

    def test_password_too_short(self) -> None:
        """PortalSetPassword requires min_length=6 (stricter than SetPasswordRequest)."""
        from models import PortalSetPassword

        with pytest.raises(ValidationError):
            PortalSetPassword(password="abcde")

    def test_missing_password_raises(self) -> None:
        from models import PortalSetPassword

        with pytest.raises(ValidationError):
            PortalSetPassword()

    def test_html_not_stripped(self) -> None:
        """password is in _SKIP_SANITIZE."""
        from models import PortalSetPassword

        m = PortalSetPassword(password="<secret>abc</secret>def")
        assert m.password == "<secret>abc</secret>def"


class TestForgotPasswordRequest:
    def test_valid(self) -> None:
        from models import ForgotPasswordRequest

        m = ForgotPasswordRequest(email="user@example.com")
        assert m.email == "user@example.com"

    def test_email_too_short(self) -> None:
        from models import ForgotPasswordRequest

        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="ab")

    def test_missing_email_raises(self) -> None:
        from models import ForgotPasswordRequest

        with pytest.raises(ValidationError):
            ForgotPasswordRequest()


class TestResetPasswordRequest:
    def test_valid(self) -> None:
        from models import ResetPasswordRequest

        m = ResetPasswordRequest(password="newpass123", token="reset-abc-123")
        assert m.password == "newpass123"
        assert m.token == "reset-abc-123"

    def test_password_too_short(self) -> None:
        """ResetPasswordRequest requires min_length=6."""
        from models import ResetPasswordRequest

        with pytest.raises(ValidationError):
            ResetPasswordRequest(password="abcde", token="valid-token")

    def test_empty_token_raises(self) -> None:
        from models import ResetPasswordRequest

        with pytest.raises(ValidationError):
            ResetPasswordRequest(password="newpass123", token="")

    def test_missing_token_raises(self) -> None:
        from models import ResetPasswordRequest

        with pytest.raises(ValidationError):
            ResetPasswordRequest(password="newpass123")
