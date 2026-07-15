import pytest
from pydantic import ValidationError


def test_login_request_valid():
    from models.auth import LoginRequest

    r = LoginRequest(email="a@b.com", password="s")
    assert r.email == "a@b.com"


def test_login_request_invalid():
    from models.auth import LoginRequest

    with pytest.raises(ValidationError):
        LoginRequest(email="a@", password="s")
    with pytest.raises(ValidationError):
        LoginRequest(email="a@b.com", password="")


def test_set_password_request():
    from models.auth import SetPasswordRequest

    r = SetPasswordRequest(password="newpass")
    assert r.password == "newpass"
