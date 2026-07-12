import pytest
from pydantic import ValidationError
def test_user_create_valid():
    from models.user import UserCreate
    u = UserCreate(name="Test", email="a@b.com", role="admin")
    assert u.name == "Test"
def test_user_create_default_role():
    from models.user import UserCreate
    u = UserCreate(name="Tech", email="t@b.com")
    assert u.role == "tech"
def test_user_update():
    from models.user import UserUpdate
    u = UserUpdate(name="U", email="u@b.com", role="admin", active=True)
    assert u.active == True
def test_user_settings():
    from models.user import UserSettingsUpdate
    s = UserSettingsUpdate(theme="dark", default_ticket_status="open")
    assert s.theme == "dark"
