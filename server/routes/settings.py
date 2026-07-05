"""Settings routes — Mail + SMS."""
from fastapi import APIRouter, Depends, HTTPException, Request

from helpers import (
    require_role, logger,
)
from mail import get_settings as _mail_get, update_settings as _mail_update, test_connection as _mail_test
from models import MailSettingsUpdate, SMSSettingsUpdate, BusinessHoursUpdate
from rate_limit import limiter
from sms import get_settings as _sms_get, update_settings as _sms_update, test_connection as _sms_test
from business_hours import get_settings as _bh_get, DEFAULT_HOURS, update_settings as _bh_update

router = APIRouter()


@router.get("/api/settings/mail")
async def mail_settings_get(user: dict = Depends(require_role("admin"))):
    """Get current mail settings (without password)."""
    settings = _mail_get()
    if settings is None:
        return {"configured": False, "settings": None}
    return {"configured": True, "settings": settings}


@router.post("/api/settings/mail")
@limiter.limit("30/minute")
async def mail_settings_save(request: Request, body: MailSettingsUpdate, user: dict = Depends(require_role("admin"))):
    """Save mail settings."""
    data = {
        "host": body.smtp_host,
        "port": body.smtp_port,
        "username": body.smtp_user,
        "password": body.smtp_password,
        "sender_email": body.smtp_from_email,
        "sender_name": body.smtp_from_name,
        "use_tls": body.smtp_tls,
    }
    _mail_update(data)
    return {"ok": True}


@router.post("/api/settings/mail/test")
@limiter.limit("10/minute")
async def mail_settings_test(request: Request, user: dict = Depends(require_role("admin"))):
    """Test SMTP connection with current settings."""
    result = _mail_test()
    return result


@router.get("/api/settings/sms")
async def sms_settings_get(user: dict = Depends(require_role("admin"))):
    """Get current SMS settings."""
    settings = _sms_get()
    if settings is None:
        return {"configured": False, "settings": None}
    return {"configured": True, "settings": settings}


@router.post("/api/settings/sms")
@limiter.limit("30/minute")
async def sms_settings_save(request: Request, body: SMSSettingsUpdate, user: dict = Depends(require_role("admin"))):
    """Save SMS settings."""
    _sms_update(data)
    return {"ok": True}


@router.post("/api/settings/sms/test")
@limiter.limit("10/minute")
async def sms_settings_test(request: Request, user: dict = Depends(require_role("admin"))):
    """Test SMS connection with current settings."""
    result = _sms_test()
    return result


# ── Business Hours ─────────────────────────────────────────────────


@router.get("/api/settings/business-hours")
async def business_hours_get(user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """Get current business hours."""
    settings = _bh_get()
    if settings is None:
        return {"configured": False, "hours": DEFAULT_HOURS}
    return {"configured": True, "hours": settings}


@router.post("/api/settings/business-hours")
@limiter.limit("30/minute")
async def business_hours_save(request: Request, body: BusinessHoursUpdate, user: dict = Depends(require_role("admin"))):
    """Save business hours."""
    data = body.model_dump()
    result = _bh_update(data)
    return {"ok": True, "hours": result}
