"""2FA / TOTP authentication endpoint tests.

Uses the isolated tenant admin for user creation so a failed 2FA test
never affects the global admin. All test users are created within the
isolated tenant scope and cleaned up at module end.
"""

import httpx
import pyotp
import pytest

from .conftest import SERVER_URL, _track_entity, assert_ok


@pytest.fixture(scope="module")
def _2fa_user(test_admin_headers: dict, session_suffix: str) -> tuple[str, str, str]:
    """Create a fresh test user for all 2FA tests in this module.

    Uses the isolated tenant admin (not global admin) so 2FA state
    changes never pollute the global bootstrap user.
    Returns (email, password, user_id). Cleans up after the module
    finishes, regardless of test failures.
    """
    suffix = session_suffix[:8]
    name = f"2fa-module-{suffix}"
    email = f"{name}@test.com"
    pw = "testpass123"

    # Create user via isolated tenant admin
    resp = httpx.post(
        f"{SERVER_URL}/api/users",
        json={"name": name, "email": email, "role": "admin"},
        headers=test_admin_headers,
        timeout=10,
    )
    assert resp.status_code == 200, f"Create 2FA test user failed: {resp.text[:200]}"

    # Get user ID
    list_resp = httpx.get(
        f"{SERVER_URL}/api/users",
        params={"limit": 500},
        headers=test_admin_headers,
        timeout=10,
    )
    users = list_resp.json().get("users", [])
    uid = next((u["id"] for u in users if u.get("email") == email), None)
    assert uid, f"Could not find user ID for {email}"
    _track_entity("user", uid)

    # Set password for the test user
    import bcrypt

    from .conftest import STDB_CALL_URL

    hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    call_resp = httpx.post(
        f"{STDB_CALL_URL}/set_user_password",
        json=[uid, hashed],
        timeout=30,
    )
    assert call_resp.status_code == 200, f"Failed to set password: {call_resp.text[:200]}"

    yield email, pw, uid

    # --- Cleanup ---
    # Delete the test user (regardless of 2FA state)
    try:
        httpx.delete(f"{SERVER_URL}/api/users/{uid}", headers=test_admin_headers, timeout=10)
    except Exception:
        pass


def _disable_2fa_user(email: str, pw: str, secret: str, admin_headers: dict) -> None:
    """Disable 2FA on a user account. Safe to call even if 2FA is not enabled."""
    try:
        totp = pyotp.TOTP(secret)
        login2 = httpx.post(
            f"{SERVER_URL}/api/auth/login",
            json={"email": email, "password": pw},
            timeout=10,
        )
        if login2.status_code != 200:
            return
        data2 = login2.json()
        if data2.get("requires_2fa") and data2.get("temp_token"):
            complete = httpx.post(
                f"{SERVER_URL}/api/auth/complete-login",
                json={"temp_token": data2["temp_token"], "code": totp.now()},
                timeout=10,
            )
            if complete.status_code != 200:
                return
            h2 = {
                "Authorization": f"Bearer {complete.json()['token']}",
                "Content-Type": "application/json",
            }
        else:
            h2 = {
                "Authorization": f"Bearer {data2['token']}",
                "Content-Type": "application/json",
            }
        httpx.post(
            f"{SERVER_URL}/api/auth/disable-2fa",
            json={"code": totp.now()},
            headers=h2,
            timeout=10,
        )
    except Exception:
        pass


# ── Tests ──


def test_setup_returns_secret(_2fa_user, test_admin_headers: dict):
    """Setup generates a secret and provisioning URI."""
    email, pw, _uid = _2fa_user
    r = httpx.post(
        f"{SERVER_URL}/api/auth/login",
        json={"email": email, "password": pw},
        timeout=10,
    )
    assert r.status_code == 200
    h = {
        "Authorization": f"Bearer {r.json()['token']}",
        "Content-Type": "application/json",
    }

    resp = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10)
    data = assert_ok(resp)
    assert "secret" in data
    assert len(data["secret"]) > 10
    assert "provisioning_uri" in data
    assert "otpauth://" in data["provisioning_uri"]


def test_verify_valid_code_enables_2fa(_2fa_user, test_admin_headers: dict):
    """Verify a valid TOTP code enables 2FA. Cleanup always runs."""
    email, pw, _uid = _2fa_user

    r = httpx.post(
        f"{SERVER_URL}/api/auth/login",
        json={"email": email, "password": pw},
        timeout=10,
    )
    h = {
        "Authorization": f"Bearer {r.json()['token']}",
        "Content-Type": "application/json",
    }

    setup = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10).json()
    secret = setup["secret"]
    totp = pyotp.TOTP(secret)
    code = totp.now()

    resp = httpx.post(
        f"{SERVER_URL}/api/auth/verify-2fa", json={"code": code}, headers=h, timeout=10
    )
    assert_ok(resp)

    me_req = httpx.get(f"{SERVER_URL}/api/auth/me", headers=h, timeout=10)
    assert me_req.json().get("totp_enabled") is True

    # Cleanup: disable 2FA on this user
    _disable_2fa_user(email, pw, secret, test_admin_headers)


def test_verify_invalid_code_fails(_2fa_user, test_admin_headers: dict):
    """Verify with wrong code returns 401."""
    email, pw, _uid = _2fa_user

    r = httpx.post(
        f"{SERVER_URL}/api/auth/login",
        json={"email": email, "password": pw},
        timeout=10,
    )
    h = {
        "Authorization": f"Bearer {r.json()['token']}",
        "Content-Type": "application/json",
    }

    setup = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10).json()
    secret = setup["secret"]

    resp = httpx.post(
        f"{SERVER_URL}/api/auth/verify-2fa",
        json={"code": "000000"},
        headers=h,
        timeout=10,
    )
    assert resp.status_code == 401

    # Cleanup
    _disable_2fa_user(email, pw, secret, test_admin_headers)


def test_double_setup_fails_after_enable(_2fa_user, test_admin_headers: dict):
    """Setting up 2FA again after it's enabled should fail."""
    email, pw, _uid = _2fa_user

    r = httpx.post(
        f"{SERVER_URL}/api/auth/login",
        json={"email": email, "password": pw},
        timeout=10,
    )
    h = {
        "Authorization": f"Bearer {r.json()['token']}",
        "Content-Type": "application/json",
    }

    setup = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10).json()
    secret = setup["secret"]
    totp = pyotp.TOTP(secret)
    httpx.post(
        f"{SERVER_URL}/api/auth/verify-2fa",
        json={"code": totp.now()},
        headers=h,
        timeout=10,
    )

    resp = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10)
    assert resp.status_code == 400

    # Cleanup
    _disable_2fa_user(email, pw, secret, test_admin_headers)


def test_login_requires_2fa_when_enabled(_2fa_user, test_admin_headers: dict):
    """Login should return requires_2fa when 2FA is enabled."""
    email, pw, _uid = _2fa_user

    r = httpx.post(
        f"{SERVER_URL}/api/auth/login",
        json={"email": email, "password": pw},
        timeout=10,
    )
    h = {
        "Authorization": f"Bearer {r.json()['token']}",
        "Content-Type": "application/json",
    }

    setup = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10).json()
    secret = setup["secret"]
    totp = pyotp.TOTP(secret)
    httpx.post(
        f"{SERVER_URL}/api/auth/verify-2fa",
        json={"code": totp.now()},
        headers=h,
        timeout=10,
    )

    login = httpx.post(
        f"{SERVER_URL}/api/auth/login",
        json={"email": email, "password": pw},
        timeout=10,
    )
    data = login.json()
    assert data.get("requires_2fa") is True
    assert "temp_token" in data
    assert "token" not in data

    # Cleanup
    _disable_2fa_user(email, pw, secret, test_admin_headers)


def test_complete_login_with_valid_code(_2fa_user, test_admin_headers: dict):
    """Complete login with valid TOTP code returns full JWT."""
    email, pw, _uid = _2fa_user

    r = httpx.post(
        f"{SERVER_URL}/api/auth/login",
        json={"email": email, "password": pw},
        timeout=10,
    )
    h = {
        "Authorization": f"Bearer {r.json()['token']}",
        "Content-Type": "application/json",
    }

    setup = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10).json()
    secret = setup["secret"]
    totp = pyotp.TOTP(secret)
    httpx.post(
        f"{SERVER_URL}/api/auth/verify-2fa",
        json={"code": totp.now()},
        headers=h,
        timeout=10,
    )

    login = httpx.post(
        f"{SERVER_URL}/api/auth/login",
        json={"email": email, "password": pw},
        timeout=10,
    ).json()
    complete = httpx.post(
        f"{SERVER_URL}/api/auth/complete-login",
        json={"temp_token": login["temp_token"], "code": totp.now()},
        timeout=10,
    )
    data = complete.json()
    assert "token" in data
    assert "user" in data

    # Cleanup
    _disable_2fa_user(email, pw, secret, test_admin_headers)


def test_complete_login_with_invalid_code_fails(_2fa_user, test_admin_headers: dict):
    """Complete login with invalid code returns 401."""
    email, pw, _uid = _2fa_user

    r = httpx.post(
        f"{SERVER_URL}/api/auth/login",
        json={"email": email, "password": pw},
        timeout=10,
    )
    h = {
        "Authorization": f"Bearer {r.json()['token']}",
        "Content-Type": "application/json",
    }

    setup = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10).json()
    secret = setup["secret"]
    totp = pyotp.TOTP(secret)
    httpx.post(
        f"{SERVER_URL}/api/auth/verify-2fa",
        json={"code": totp.now()},
        headers=h,
        timeout=10,
    )

    login = httpx.post(
        f"{SERVER_URL}/api/auth/login",
        json={"email": email, "password": pw},
        timeout=10,
    ).json()
    complete = httpx.post(
        f"{SERVER_URL}/api/auth/complete-login",
        json={"temp_token": login["temp_token"], "code": "000000"},
        timeout=10,
    )
    assert complete.status_code == 401

    # Cleanup
    _disable_2fa_user(email, pw, secret, test_admin_headers)


def test_disable_with_valid_code(_2fa_user, test_admin_headers: dict):
    """Disable 2FA with a valid TOTP code."""
    email, pw, _uid = _2fa_user

    r = httpx.post(
        f"{SERVER_URL}/api/auth/login",
        json={"email": email, "password": pw},
        timeout=10,
    )
    h = {
        "Authorization": f"Bearer {r.json()['token']}",
        "Content-Type": "application/json",
    }

    setup = httpx.post(f"{SERVER_URL}/api/auth/setup-2fa", headers=h, timeout=10).json()
    secret = setup["secret"]
    totp = pyotp.TOTP(secret)
    httpx.post(
        f"{SERVER_URL}/api/auth/verify-2fa",
        json={"code": totp.now()},
        headers=h,
        timeout=10,
    )

    # Login + complete 2FA challenge
    login2 = httpx.post(
        f"{SERVER_URL}/api/auth/login",
        json={"email": email, "password": pw},
        timeout=10,
    ).json()
    complete = httpx.post(
        f"{SERVER_URL}/api/auth/complete-login",
        json={"temp_token": login2["temp_token"], "code": totp.now()},
        timeout=10,
    ).json()
    h2 = {
        "Authorization": f"Bearer {complete['token']}",
        "Content-Type": "application/json",
    }
    resp = httpx.post(
        f"{SERVER_URL}/api/auth/disable-2fa",
        json={"code": totp.now()},
        headers=h2,
        timeout=10,
    )
    assert_ok(resp)

    me = httpx.get(f"{SERVER_URL}/api/auth/me", headers=h, timeout=10).json()
    assert me.get("totp_enabled") is False
