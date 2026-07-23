"""2FA models — fixed-length digit pattern."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestSetup2FARequest:
    def test_valid(self) -> None:
        from models import Setup2FARequest

        m = Setup2FARequest(code="123456")
        assert m.code == "123456"

    def test_code_contains_letters_raises(self) -> None:
        from models import Setup2FARequest

        with pytest.raises(ValidationError):
            Setup2FARequest(code="12345a")

    def test_code_too_short(self) -> None:
        """min_length=6, max_length=6, so 5 chars fails."""
        from models import Setup2FARequest

        with pytest.raises(ValidationError):
            Setup2FARequest(code="12345")

    def test_code_too_long(self) -> None:
        from models import Setup2FARequest

        with pytest.raises(ValidationError):
            Setup2FARequest(code="1234567")

    def test_empty_code_raises(self) -> None:
        from models import Setup2FARequest

        with pytest.raises(ValidationError):
            Setup2FARequest(code="")


class TestCompleteLoginRequest:
    def test_valid(self) -> None:
        from models import CompleteLoginRequest

        m = CompleteLoginRequest(temp_token="temp-abc", code="654321")
        assert m.temp_token == "temp-abc"
        assert m.code == "654321"

    def test_invalid_code_pattern(self) -> None:
        from models import CompleteLoginRequest

        with pytest.raises(ValidationError):
            CompleteLoginRequest(temp_token="tok", code="abcd12")

    def test_empty_temp_token_raises(self) -> None:
        from models import CompleteLoginRequest

        with pytest.raises(ValidationError):
            CompleteLoginRequest(temp_token="", code="123456")


class TestDisable2FARequest:
    def test_valid(self) -> None:
        from models import Disable2FARequest

        m = Disable2FARequest(code="000000")
        assert m.code == "000000"

    def test_invalid_code(self) -> None:
        from models import Disable2FARequest

        with pytest.raises(ValidationError):
            Disable2FARequest(code="abcdef")
