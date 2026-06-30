"""Auth routes — login, me, set-password, refresh-tenant."""
from datetime import datetime, timedelta
import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request

from config import settings
from helpers import (
    _sql, _call, require_role, get_current_user, logger,
)
from models import LoginRequest, SetPasswordRequest, ForgotPasswordRequest, ResetPasswordRequest
from rate_limit import limiter

router = APIRouter()


@router.post("/api/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, login_data: LoginRequest):
    """Login with email + password, returns JWT token."""
    email = login_data.email
    password = login_data.password

    if not email or not password:
        raise HTTPException(400, "Email and password required")

    rows = await _sql(f"SELECT * FROM user WHERE email = '{email}'")
    if not rows:
        raise HTTPException(401, "Invalid email or password")

    user = rows[0]
    pw_hash = user.get("password_hash", "")

    if not pw_hash or not bcrypt.checkpw(password.encode(), pw_hash.encode()):
        raise HTTPException(401, "Invalid email or password")

    if not user.get("active", False):
        raise HTTPException(403, "Account is disabled")

    now = datetime.utcnow()

    tenant_id = ""
    try:
        tm_rows = await _sql(f"SELECT * FROM tenant_members WHERE username = '{user['name']}'")
        if tm_rows:
            tenant_id = tm_rows[0]["tenant_id"]
    except Exception:
        pass

    token = jwt.encode(
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
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "tenant_id": user.get("tenant_id", ""),
        "tenant": tenant_info,
    }


@router.post("/api/auth/refresh-tenant")
async def refresh_token_tenant(user: dict = Depends(get_current_user)):
    """Refresh the JWT token with latest tenant_id from DB."""
    tid = ""
    try:
        tm_rows = await _sql(f"SELECT * FROM tenant_members WHERE username = '{user['name']}'")
        if tm_rows:
            tid = tm_rows[0]["tenant_id"]
    except Exception:
        pass
    now = datetime.utcnow()
    token = jwt.encode(
        {
            "sub": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "tenant_id": tid,
            "iat": now,
            "exp": now + timedelta(hours=settings.jwt_expire_hours),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"token": token, "tenant_id": tid}


@router.post("/api/auth/set-password")
async def set_password(body: SetPasswordRequest, user: dict = Depends(get_current_user)):
    """Set/change password for current user."""
    pw = body.password
    if len(pw) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    await _call("set_user_password", [user["id"], hashed])  # noqa: F821
    return {"ok": True}


# ── Password Reset ─────────────────────────────────────────────


@router.post("/api/auth/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(request: Request, body: ForgotPasswordRequest):
    """Send a password-reset email if the email exists.

    Always returns 200 to avoid revealing whether the email exists.
    """
    email = body.email.strip().lower()
    if not email:
        raise HTTPException(400, "Email is required")

    # Find user (staff or customer)
    user = None
    user_type = None
    rows = await _sql(f"SELECT * FROM user WHERE email = '{email}'")
    if rows:
        user = rows[0]
        user_type = "staff"
    else:
        rows = await _sql(f"SELECT * FROM customer WHERE email = '{email}'")
        if rows:
            user = rows[0]
            user_type = "customer"

    if user is None:
        logger.info("Password reset requested for unknown email: %s", email)
        return {"ok": True, "message": "If that email exists, a reset link has been sent."}

    # Generate short-lived JWT reset token (15 minutes)
    now = datetime.utcnow()
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

    from mail import send_email as _send_email

    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#333">Password Reset</h2>
<p>You requested a password reset for your SpacetimeCRM account.</p>
<p><a href="{reset_link}" style="display:inline-block;background:#6366f1;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none">Reset Password</a></p>
<p style="color:#999;font-size:13px">This link expires in 15 minutes. If you didn't request this, you can safely ignore this email.</p>
<hr style="border:none;border-top:1px solid #eee" />
<p style="color:#999;font-size:12px">SpacetimeCRM</p>
</body></html>"""
    _send_email(email, "Password Reset — SpacetimeCRM", html)

    logger.info("Password reset email sent to %s (%s)", email, user_type)
    return {"ok": True, "message": "If that email exists, a reset link has been sent."}


@router.post("/api/auth/reset-password")
@limiter.limit("5/minute")
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
