"""User models — role regex."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestUserCreate:
    def test_valid(self) -> None:
        from models import UserCreate

        m = UserCreate(name="Alice Admin", email="alice@example.com")
        assert m.name == "Alice Admin"
        assert m.email == "alice@example.com"
        assert m.role == "tech"  # default

    def test_valid_roles(self) -> None:
        from models import UserCreate

        for role in ("admin", "tech", "front_desk"):
            m = UserCreate(name="User", email="user@example.com", role=role)
            assert m.role == role

    def test_invalid_role(self) -> None:
        from models import UserCreate

        with pytest.raises(ValidationError, match="role"):
            UserCreate(name="Hacker", email="hacker@example.com", role="superadmin")

    def test_name_too_short(self) -> None:
        from models import UserCreate

        with pytest.raises(ValidationError):
            UserCreate(name="", email="a@b.com")

    def test_name_too_long(self) -> None:
        from models import UserCreate

        with pytest.raises(ValidationError):
            UserCreate(name="x" * 101, email="a@b.com")

    def test_email_too_long(self) -> None:
        from models import UserCreate

        with pytest.raises(ValidationError):
            UserCreate(name="Alice", email="x" * 256)

    def test_missing_name_raises(self) -> None:
        from models import UserCreate

        with pytest.raises(ValidationError):
            UserCreate(email="a@b.com")


class TestUserUpdate:
    def test_valid(self) -> None:
        from models import UserUpdate

        m = UserUpdate(name="Alice Updated", email="alice@new.com", role="admin")
        assert m.active is True  # default

    def test_invalid_role(self) -> None:
        from models import UserUpdate

        with pytest.raises(ValidationError):
            UserUpdate(name="Bob", email="b@b.com", role="manager")


class TestUserSettingsUpdate:
    def test_valid_theme_default(self) -> None:
        from models import UserSettingsUpdate

        m = UserSettingsUpdate()
        assert m.theme == "light"
        assert m.default_ticket_status == "new"

    def test_invalid_theme(self) -> None:
        from models import UserSettingsUpdate

        with pytest.raises(ValidationError, match="theme"):
            UserSettingsUpdate(theme="neon")

    def test_valid_themes(self) -> None:
        from models import UserSettingsUpdate

        for theme in ("light", "dark"):
            m = UserSettingsUpdate(theme=theme)
            assert m.theme == theme

    def test_default_ticket_status_max_length(self) -> None:
        from models import UserSettingsUpdate

        with pytest.raises(ValidationError):
            UserSettingsUpdate(default_ticket_status="x" * 51)
