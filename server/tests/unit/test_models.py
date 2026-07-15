"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError


def test_login_request_valid():
    from models.auth import LoginRequest

    r = LoginRequest(email="a@b.com", password="secret123")
    assert r.email == "a@b.com"
    assert r.password == "secret123"


def test_login_request_invalid():
    from models.auth import LoginRequest

    with pytest.raises(ValidationError):
        LoginRequest(email="", password="x")
    with pytest.raises(ValidationError):
        LoginRequest(email="a@b.com", password="")


def test_login_request_short_email():
    from models.auth import LoginRequest

    with pytest.raises(ValidationError):
        LoginRequest(email="a@", password="x")  # min_length=3


def test_set_password_request():
    from models.auth import SetPasswordRequest

    r = SetPasswordRequest(password="newpass")
    assert r.password == "newpass"


def test_user_create_valid():
    from models.user import UserCreate

    u = UserCreate(name="Test User", email="a@b.com", role="admin")
    assert u.name == "Test User"
    assert u.email == "a@b.com"
    assert u.role == "admin"


def test_user_create_default_role():
    from models.user import UserCreate

    u = UserCreate(name="Tech User", email="tech@b.com")
    assert u.role == "tech"


def test_user_create_invalid():
    from models.user import UserCreate

    with pytest.raises(ValidationError):
        UserCreate(name="", email="a@b.com")  # empty name


def test_user_create_invalid_role():
    from models.user import UserCreate

    with pytest.raises(ValidationError):
        UserCreate(name="Test", email="a@b.com", role="invalid_role")


def test_user_update():
    from models.user import UserUpdate

    u = UserUpdate(name="Updated", email="u@b.com", role="admin", active=True)
    assert u.name == "Updated"
    assert u.active == True


def test_user_settings_update():
    from models.user import UserSettingsUpdate

    s = UserSettingsUpdate(theme="dark", default_ticket_status="open")
    assert s.theme == "dark"


def test_user_settings_update_invalid_theme():
    from models.user import UserSettingsUpdate

    with pytest.raises(ValidationError):
        UserSettingsUpdate(theme="red")  # must be light or dark


def test_customer_create():
    from models.customers import CustomerCreate

    c = CustomerCreate(first_name="John", last_name="Doe", email="j@d.com")
    assert c.first_name == "John"
    assert c.last_name == "Doe"


def test_customer_create_missing_first_name():
    from models.customers import CustomerCreate

    with pytest.raises(ValidationError):
        CustomerCreate(first_name="", last_name="Doe")


def test_customer_update():
    from models.customers import CustomerUpdate

    c = CustomerUpdate(first_name="Jane", last_name="Doe")
    assert c.first_name == "Jane"
