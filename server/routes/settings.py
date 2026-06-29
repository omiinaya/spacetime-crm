"""Settings routes — Mail + SMS."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from helpers import (
    require_role, logger,
)
from models import MailSettingsUpdate, SMSSettingsUpdate
from rate_limit import limiter

router = APIRouter()


@router.get("/api/settings/mail")
async def mail_settings_get(user: dict = Depends(require_role("admin"))):
    """Get current mail settings (without password)."""
    from mail import get_settings as _get
    settings = _get()
    if settings is None:
        return {"configured": False, "settings": None}
    return {"configured": True, "settings": settings}


@router.post("/api/settings/mail")
@limiter.limit("30/minute")
async def mail_settings_save(request: Request, body: MailSettingsUpdate, user: dict = Depends(require_role("admin"))):
    """Save mail settings."""
    from mail import update_settings as _update
    data = {
        "host": body.smtp_host,
        "port": body.smtp_port,
        "username": body.smtp_user,
        "password": body.smtp_password,
        "sender_email": body.smtp_from_email,
        "sender_name": body.smtp_from_name,
        "use_tls": body.smtp_tls,
    }
    _update(data)
    return {"ok": True}


@router.post("/api/settings/mail/test")
@limiter.limit("10/minute")
async def mail_settings_test(request: Request, user: dict = Depends(require_role("admin"))):
    """Test SMTP connection with current settings."""
    from mail import test_connection as _test
    result = _test()
    return result


@router.get("/api/settings/sms")
async def sms_settings_get(user: dict = Depends(require_role("admin"))):
    """Get current SMS settings."""
    from sms import get_settings as _get
    settings = _get()
    if settings is None:
        return {"configured": False, "settings": None}
    return {"configured": True, "settings": settings}


@router.post("/api/settings/sms")
@limiter.limit("30/minute")
async def sms_settings_save(request: Request, body: SMSSettingsUpdate, user: dict = Depends(require_role("admin"))):
    """Save SMS settings."""
    from sms import update_settings as _update
    data = {
        "account_sid": body.twilio_account_sid,
        "auth_token": body.twilio_auth_token,
        "from_number": body.twilio_from_number,
    }
    _update(data)
    return {"ok": True}


@router.post("/api/settings/sms/test")
@limiter.limit("10/minute")
async def sms_settings_test(request: Request, user: dict = Depends(require_role("admin"))):
    """Test SMS connection with current settings."""
    from sms import test_connection as _test
    result = _test()
    return result
