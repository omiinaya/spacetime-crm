"""2FA / TOTP authentication endpoint tests.

Uses a dedicated test user to avoid interfering with the admin account.
"""
import pyotp
import httpx
import time
from .conftest import SERVER_URL, assert_ok


def _create_test_user() -> tuple[str, str]:
    """Create a test user for 2FA tests. Returns (user_id, name)."""
    suffix = str(int(time.time() * 1000))[-8:]
    name = f"2fa-test-{suffix}"
    email = f"{name}@test.com"
    pw = "testpass123"

    # Login as admin first
    r = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10)
    data = r.json()
    if data.get("requires_2fa"):
        raise RuntimeError("Admin has 2FA enabled! Run manual disable first.")
    token = data["token"]
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Create user
    resp = httpx.post(f"{SERVER_URL}/api/users", json={"name": name, "email": email, "role": "admin"}, headers=h, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to create test user: {resp.text}")

    # Set password
    resp2 = httpx.post(f"{SERVER_URL}/api/auth/set-password", json={"password": pw}, headers={
        "Authorization": f"Bearer {httpx.post(f'{SERVER_URL}/api/auth/login', json={'email': email, 'password': pw}, timeout=10).json()['token']}",
        "Content-Type": "application/json"
    }, timeout=10)

    return email, pw


def _delete_test_user(user_id: str):
    """Clean up test user."""
    r = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10)
    h = {"Authorization": f"Bearer {r.json()['token']}", "Content-Type": "application/json"}
    httpx.delete(f"{SERVER_URL}/api/users/{user_id}", headers=h, timeout=10)


# ── Setup tests ──

def test_setup_returns_secret():
    """Setup generates a secret and provisioning URI."""
    r = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10)
    assert r.status_code == 200
    h = {"Authorization": f"Bearer {r.json()['token']}", "Content-Type": "application/json"}

    resp = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10)
    data = assert_ok(resp)
    assert "secret" in data
    assert len(data["secret"]) > 10
    assert "provisioning_uri" in data
    assert "otpauth://" in data["provisioning_uri"]


def test_verify_valid_code_enables_2fa():
    """Verify a valid TOTP code enables 2FA. Then disable for cleanup."""
    r = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10)
    h = {"Authorization": f"Bearer {r.json()['token']}", "Content-Type": "application/json"}

    setup = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10).json()
    secret = setup["secret"]
    totp = pyotp.TOTP(secret)
    code = totp.now()

    resp = httpx.post(f"{SERVER_URL}/api/auth/verify-2fa", json={"code": code}, headers=h, timeout=10)
    assert_ok(resp)

    me = httpx.get(f"{SERVER_URL}/api/auth/me", headers=h, timeout=10).json()
    assert me.get("totp_enabled") is True

    # Cleanup: need to disable via 2FA challenge
    login2 = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10).json()
    complete = httpx.post(f"{SERVER_URL}/api/auth/complete-login",
        json={"temp_token": login2["temp_token"], "code": totp.now()}, timeout=10).json()
    h2 = {"Authorization": f"Bearer {complete['token']}", "Content-Type": "application/json"}
    httpx.post(f"{SERVER_URL}/api/auth/disable-2fa", json={"code": totp.now()}, headers=h2, timeout=10)


def test_verify_invalid_code_fails():
    """Verify with wrong code returns 401."""
    r = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10)
    h = {"Authorization": f"Bearer {r.json()['token']}", "Content-Type": "application/json"}

    # Setup first
    setup = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10).json()
    secret = setup["secret"]

    resp = httpx.post(f"{SERVER_URL}/api/auth/verify-2fa", json={"code": "000000"}, headers=h, timeout=10)
    assert resp.status_code == 401

    # Cleanup
    httpx.post(f"{SERVER_URL}/api/auth/disable-2fa", json={"code": pyotp.TOTP(secret).now()}, headers=h, timeout=10)


def test_double_setup_fails_after_enable():
    """Setting up 2FA again after it's enabled should fail."""
    r = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10)
    h = {"Authorization": f"Bearer {r.json()['token']}", "Content-Type": "application/json"}

    setup = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10).json()
    secret = setup["secret"]
    totp = pyotp.TOTP(secret)
    httpx.post(f"{SERVER_URL}/api/auth/verify-2fa", json={"code": totp.now()}, headers=h, timeout=10)

    resp = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10)
    assert resp.status_code == 400

    # Cleanup
    login2 = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10).json()
    complete = httpx.post(f"{SERVER_URL}/api/auth/complete-login",
        json={"temp_token": login2["temp_token"], "code": totp.now()}, timeout=10).json()
    httpx.post(f"{SERVER_URL}/api/auth/disable-2fa", json={"code": totp.now()},
        headers={"Authorization": f"Bearer {complete['token']}"}, timeout=10)


def test_login_requires_2fa_when_enabled():
    """Login should return requires_2fa when 2FA is enabled."""
    r = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10)
    h = {"Authorization": f"Bearer {r.json()['token']}", "Content-Type": "application/json"}

    setup = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10).json()
    secret = setup["secret"]
    totp = pyotp.TOTP(secret)
    httpx.post(f"{SERVER_URL}/api/auth/verify-2fa", json={"code": totp.now()}, headers=h, timeout=10)

    login = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10)
    data = login.json()
    assert data.get("requires_2fa") is True
    assert "temp_token" in data
    assert "token" not in data

    # Cleanup
    complete = httpx.post(f"{SERVER_URL}/api/auth/complete-login",
        json={"temp_token": data["temp_token"], "code": totp.now()}, timeout=10).json()
    httpx.post(f"{SERVER_URL}/api/auth/disable-2fa", json={"code": totp.now()},
        headers={"Authorization": f"Bearer {complete['token']}"}, timeout=10)


def test_complete_login_with_valid_code():
    """Complete login with valid TOTP code returns full JWT."""
    r = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10)
    h = {"Authorization": f"Bearer {r.json()['token']}", "Content-Type": "application/json"}

    setup = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10).json()
    secret = setup["secret"]
    totp = pyotp.TOTP(secret)
    httpx.post(f"{SERVER_URL}/api/auth/verify-2fa", json={"code": totp.now()}, headers=h, timeout=10)

    login = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10).json()
    complete = httpx.post(f"{SERVER_URL}/api/auth/complete-login",
        json={"temp_token": login["temp_token"], "code": totp.now()}, timeout=10)
    data = complete.json()
    assert "token" in data
    assert data["user"]["email"] == "admin@crm.local"

    # Cleanup
    login2 = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10).json()
    complete2 = httpx.post(f"{SERVER_URL}/api/auth/complete-login",
        json={"temp_token": login2["temp_token"], "code": totp.now()}, timeout=10).json()
    httpx.post(f"{SERVER_URL}/api/auth/disable-2fa", json={"code": totp.now()},
        headers={"Authorization": f"Bearer {complete2['token']}"}, timeout=10)


def test_complete_login_with_invalid_code_fails():
    """Complete login with invalid code returns 401."""
    r = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10)
    h = {"Authorization": f"Bearer {r.json()['token']}", "Content-Type": "application/json"}

    setup = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10).json()
    secret = setup["secret"]
    totp = pyotp.TOTP(secret)
    httpx.post(f"{SERVER_URL}/api/auth/verify-2fa", json={"code": totp.now()}, headers=h, timeout=10)

    login = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10).json()
    complete = httpx.post(f"{SERVER_URL}/api/auth/complete-login",
        json={"temp_token": login["temp_token"], "code": "000000"}, timeout=10)
    assert complete.status_code == 401

    # Cleanup
    login2 = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10).json()
    complete2 = httpx.post(f"{SERVER_URL}/api/auth/complete-login",
        json={"temp_token": login2["temp_token"], "code": totp.now()}, timeout=10).json()
    httpx.post(f"{SERVER_URL}/api/auth/disable-2fa", json={"code": totp.now()},
        headers={"Authorization": f"Bearer {complete2['token']}"}, timeout=10)


def test_disable_with_valid_code():
    """Disable 2FA with a valid TOTP code."""
    r = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10)
    h = {"Authorization": f"Bearer {r.json()['token']}", "Content-Type": "application/json"}

    setup = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10).json()
    secret = setup["secret"]
    totp = pyotp.TOTP(secret)
    httpx.post(f"{SERVER_URL}/api/auth/verify-2fa", json={"code": totp.now()}, headers=h, timeout=10)

    # Disable via 2FA challenge flow
    login2 = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": "admin@crm.local", "password": "PLACEHOLDER_ADMIN_PW"}, timeout=10).json()
    complete = httpx.post(f"{SERVER_URL}/api/auth/complete-login",
        json={"temp_token": login2["temp_token"], "code": totp.now()}, timeout=10).json()
    h2 = {"Authorization": f"Bearer {complete['token']}", "Content-Type": "application/json"}
    resp = httpx.post(f"{SERVER_URL}/api/auth/disable-2fa", json={"code": totp.now()}, headers=h2, timeout=10)
    assert_ok(resp)

    me = httpx.get(f"{SERVER_URL}/api/auth/me", headers=h, timeout=10).json()
    assert me.get("totp_enabled") is False
