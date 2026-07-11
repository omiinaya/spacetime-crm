"""Auth routes — login, me, set-password, refresh-tenant, 2FA/TOTP."""
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request

from config import settings
from helpers import (
    _safe_id,
    _sql, _call, require_role, get_current_user, logger,
)
from models import (
    LoginRequest, SetPasswordRequest, ForgotPasswordRequest, ResetPasswordRequest,
    Setup2FARequest, CompleteLoginRequest, Disable2FARequest,
    SetPinRequest, PosLoginRequest,
)
from rate_limit import limiter

import pyotp
import base64
import os
import json
from mail import send_email as _send_email

router = APIRouter()


TEMP_TOKEN_EXPIRE_MINUTES = 5


def _make_full_token(user: dict, tenant_id: str, now: datetime) -> str:
    """Generate a full JWT token for an authenticated user."""
    return jwt.encode(
        {
            "sub": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "tenant_id": tenant_id,
            "iat": now,
            "exp": now + timedelta(hours=settings.jwt_expire_hours),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def _make_temp_token(user: dict, now: datetime) -> str:
    """Generate a short-lived temporary token for 2FA challenge."""
    return jwt.encode(
        {
            "sub": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "purpose": "2fa_challenge",
            "iat": now,
            "exp": now + timedelta(minutes=TEMP_TOKEN_EXPIRE_MINUTES),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def _decode_temp_token(token: str) -> dict:
    """Decode and validate a temporary 2FA token. Returns payload or raises."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("purpose") != "2fa_challenge":
            raise HTTPException(400, "Invalid token purpose")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Temporary token expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(400, "Invalid temporary token.")


@router.post("/api/auth/login")
@limiter.limit("30/minute")
async def login(request: Request, login_data: LoginRequest):
    """Login with email + password. Returns JWT or 2FA challenge."""
    email = login_data.email
    password = login_data.password

    if not email or not password:
        raise HTTPException(400, "Email and password required")

    rows = await _sql(f"SELECT * FROM user WHERE email = '{_sanitize_sql(email)}'")
    if not rows:
        raise HTTPException(401, "Invalid email or password")

    user = rows[0]
    pw_hash = user.get("password_hash", "")

    if not pw_hash or not bcrypt.checkpw(password.encode(), pw_hash.encode()):
        raise HTTPException(401, "Invalid email or password")

    if not user.get("active", False):
        raise HTTPException(403, "Account is disabled")

    now = datetime.now(timezone.utc)

    # Check if 2FA is enabled
    if user.get("totp_enabled", False):
        temp_token = _make_temp_token(user, now)
        return {
            "requires_2fa": True,
            "temp_token": temp_token,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
            },
        }

    # No 2FA — return full token
    tenant_id = ""
    try:
        tm_rows = await _sql(f"SELECT * FROM tenant_members WHERE username = '{_sanitize_sql(user['name'])}'")
        if tm_rows:
            tenant_id = tm_rows[0]["tenant_id"]
    except Exception:
        pass

    token = _make_full_token(user, tenant_id, now)

    return {
        "token": token,
        "requires_2fa": False,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "tenant_id": tenant_id,
        },
    }


@router.post("/api/auth/complete-login")
@limiter.limit("30/minute")
async def complete_login(request: Request, body: CompleteLoginRequest):
    """Complete 2FA challenge and receive full JWT token."""
    payload = _decode_temp_token(body.temp_token)
    user_id = payload["sub"]

    rows = await _sql(f"SELECT * FROM user WHERE id = '{_safe_id(user_id)}'")
    if not rows:
        raise HTTPException(401, "User not found")

    user = rows[0]
    if not user.get("totp_enabled", False):
        raise HTTPException(400, "2FA is not enabled for this user")

    secret = user.get("totp_secret", "")
    if not secret:
        raise HTTPException(500, "TOTP secret not found for user with 2FA enabled")

    totp = pyotp.TOTP(secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(401, "Invalid verification code")

    now = datetime.now(timezone.utc)
    tenant_id = ""
    try:
        tm_rows = await _sql(f"SELECT * FROM tenant_members WHERE username = '{_safe_id(user['name'])}'")
        if tm_rows:
            tenant_id = tm_rows[0]["tenant_id"]
    except Exception:
        pass

    token = _make_full_token(user, tenant_id, now)

    return {
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "tenant_id": tenant_id,
        },
    }


@router.get("/api/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    """Return current user info from JWT."""
    tenant_info = {}
    if user.get("tenant_id"):
        try:
            trows = await _sql(f"SELECT * FROM tenants WHERE id = '{user['tenant_id']}'")
            if trows:
                tenant_info = trows[0]
        except Exception:
            pass

    # Check 2FA status and PIN from DB (JWT doesn't contain pin)
    totp_enabled = False
    has_pin = False
    try:
        rows = await _sql(f"SELECT * FROM user WHERE id = '{_safe_id(user['id'])}'")
        if rows:
            totp_enabled = rows[0].get("totp_enabled", False)
            has_pin = bool(rows[0].get("pin", ""))
    except Exception:
        pass

    result = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "tenant_id": user.get("tenant_id", ""),
        "tenant": tenant_info,
        "totp_enabled": totp_enabled,
        "has_pin": has_pin,
    }
    return result


@router.post("/api/auth/setup-2fa")
async def setup_2fa(user: dict = Depends(get_current_user)):
    """Generate TOTP secret and return provisioning URI for QR code."""
    # Check if already enabled
    rows = await _sql(f"SELECT * FROM user WHERE id = '{_safe_id(user['id'])}'")
    if rows and rows[0].get("totp_enabled", False):
        raise HTTPException(400, "2FA is already enabled. Disable it first to re-setup.")

    # Generate new secret
    secret = pyotp.random_base32()
    issuer = "SpacetimeCRM"
    provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user["email"],
        issuer_name=issuer,
    )

    # Store secret in DB (not yet enabled)
    await _call("set_user_totp_secret", [user["id"], secret])

    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
    }


@router.post("/api/auth/verify-2fa")
async def verify_2fa(body: Setup2FARequest, user: dict = Depends(get_current_user)):
    """Verify a TOTP code and enable 2FA."""
    rows = await _sql(f"SELECT * FROM user WHERE id = '{_safe_id(user['id'])}'")
    if not rows:
        raise HTTPException(404, "User not found")

    secret = rows[0].get("totp_secret", "")
    if not secret:
        raise HTTPException(400, "TOTP secret not found. Please run setup first.")

    totp = pyotp.TOTP(secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(401, "Invalid verification code")

    await _call("enable_user_totp", [user["id"]])
    return {"ok": True, "message": "2FA has been enabled."}


@router.post("/api/auth/disable-2fa")
async def disable_2fa(body: Disable2FARequest, user: dict = Depends(get_current_user)):
    """Verify current TOTP code and disable 2FA."""
    rows = await _sql(f"SELECT * FROM user WHERE id = '{_safe_id(user['id'])}'")
    if not rows:
        raise HTTPException(404, "User not found")

    secret = rows[0].get("totp_secret", "")
    if not secret:
        raise HTTPException(400, "2FA is not set up")

    totp = pyotp.TOTP(secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(401, "Invalid verification code")

    await _call("disable_user_totp", [user["id"]])
    return {"ok": True, "message": "2FA has been disabled."}


@router.post("/api/auth/refresh-tenant")
async def refresh_token_tenant(user: dict = Depends(get_current_user)):
    """Refresh the JWT token with latest tenant_id from DB."""
    tid = ""
    try:
        tm_rows = await _sql(f"SELECT * FROM tenant_members WHERE username = '{_safe_id(user['name'])}'")
        if tm_rows:
            tid = tm_rows[0]["tenant_id"]
    except Exception:
        pass
    now = datetime.now(timezone.utc)
    token = _make_full_token(user, tid, now)
    return {"token": token, "tenant_id": tid}


@router.post("/api/auth/set-password")
async def set_password(body: SetPasswordRequest, user: dict = Depends(get_current_user)):
    """Set/change password for current user."""
    pw = body.password
    if len(pw) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    await _call("set_user_password", [user["id"], hashed])
    return {"ok": True}


@router.post("/api/auth/set-pin")
async def set_pin(body: SetPinRequest, user: dict = Depends(get_current_user)):
    """Set, change, or remove the POS PIN for the current user. PIN is stored as bcrypt hash.
    Pass an empty string to remove the PIN."""
    pin = body.pin
    if not pin:
        # Remove PIN
        await _call("set_user_pin", [user["id"], ""])
        return {"ok": True, "message": "POS PIN removed"}
    if not pin.isdigit() or len(pin) < 4 or len(pin) > 10:
        raise HTTPException(400, "PIN must be 4–10 digits or empty to remove")
    hashed = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()
    await _call("set_user_pin", [user["id"], hashed])
    return {"ok": True}


@router.post("/api/auth/pos-login")
@limiter.limit("30/minute")
async def pos_login(request: Request, body: PosLoginRequest):
    """Quick PIN-based login for POS terminal. Returns full JWT (no 2FA challenge)."""
    user_id = body.user_id
    pin = body.pin

    if not pin.isdigit() or len(pin) < 4 or len(pin) > 10:
        raise HTTPException(400, "PIN must be 4–10 digits")

    rows = await _sql(f"SELECT * FROM user WHERE id = '{_safe_id(user_id)}'")
    if not rows:
        raise HTTPException(401, "Invalid user ID or PIN")

    user = rows[0]
    if not user.get("active", False):
        raise HTTPException(403, "Account is disabled")

    stored_pin = user.get("pin", "")
    if not stored_pin or not bcrypt.checkpw(pin.encode(), stored_pin.encode()):
        raise HTTPException(401, "Invalid user ID or PIN")

    now = datetime.now(timezone.utc)
    tenant_id = ""
    try:
        tm_rows = await _sql(f"SELECT * FROM tenant_members WHERE username = '{_safe_id(user['name'])}'")
        if tm_rows:
            tenant_id = tm_rows[0]["tenant_id"]
    except Exception:
        pass

    token = _make_full_token(user, tenant_id, now)
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "tenant_id": tenant_id,
        },
    }


# ── Password Reset ─────────────────────────────────────────────


@router.post("/api/auth/forgot-password")
@limiter.limit("10/minute")
async def forgot_password(request: Request, body: ForgotPasswordRequest):
    """Send a password-reset email if the email exists.

    Always returns 200 to avoid revealing whether the email exists.
    """
    email = body.email.strip().lower()
    if not email:
        raise HTTPException(400, "Email is required")

    user = None
    user_type = None
    rows = await _sql(f"SELECT * FROM user WHERE email = '{_safe_id(email)}'")
    if rows:
        user = rows[0]
        user_type = "staff"
    else:
        rows = await _sql(f"SELECT * FROM customer WHERE email = '{_safe_id(email)}'")
        if rows:
            user = rows[0]
            user_type = "customer"

    if user is None:
        logger.info("Password reset requested for unknown email: %s", email)
        return {"ok": True, "message": "If that email exists, a reset link has been sent."}

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": user["id"],
            "email": email,
            "type": "password_reset",
            "sub_type": user_type,
            "iat": now,
            "exp": now + timedelta(minutes=15),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    reset_link = f"{settings.app_url}/reset-password?token={token}"

    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#333">Password Reset</h2>
<p>You requested a password reset for your SpacetimeCRM account.</p>
<p><a href="{reset_link}" style="display:inline-block;background:#6366f1;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none">Reset Password</a></p>
<p style="color:#999;font-size:13px">This link expires in 15 minutes. If you didn't request this, you can safely ignore this email.</p>
<hr style="border:none;border-top:1px solid #eee" />
<p style="color:#999;font-size:12px">SpacetimeCRM</p>
</body></html>"""
    _send_email(email, "Password Reset \u2014 SpacetimeCRM", html)

    logger.info("Password reset email sent to %s (%s)", email, user_type)
    return {"ok": True, "message": "If that email exists, a reset link has been sent."}


@router.post("/api/auth/reset-password")
@limiter.limit("10/minute")
async def reset_password(request: Request, body: ResetPasswordRequest):
    """Reset password using a valid reset token."""
    token = body.token.strip()
    new_password = body.password

    if not token:
        raise HTTPException(400, "Token is required")
    if len(new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(400, "Reset token has expired. Please request a new one.")
    except jwt.InvalidTokenError:
        raise HTTPException(400, "Invalid reset token.")

    if payload.get("type") != "password_reset":
        raise HTTPException(400, "Invalid reset token.")

    user_id = payload.get("sub")
    user_type = payload.get("sub_type")
    if not user_id or not user_type:
        raise HTTPException(400, "Invalid reset token.")

    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

    if user_type == "staff":
        await _call("set_user_password", [user_id, hashed])
    elif user_type == "customer":
        await _call("set_customer_password", [user_id, hashed])
    else:
        raise HTTPException(400, "Invalid reset token.")

    logger.info("Password reset completed for %s (%s)", user_id, user_type)
    return {"ok": True, "message": "Password has been reset successfully."}
