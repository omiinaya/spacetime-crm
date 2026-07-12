"""Settings routes — Mail + SMS."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from business_hours import DEFAULT_HOURS
from business_hours import get_settings as _bh_get
from business_hours import update_settings as _bh_update
from helpers import (

    require_role,
)
from mail import get_settings as _mail_get
from mail import test_connection as _mail_test
from mail import update_settings as _mail_update
from server.models.business_hours import BusinessHoursUpdate
from server.models.mail_sms_settings import MailSettingsUpdate, SMSSettingsUpdate
router = APIRouter()


@router.get("/api/settings/mail")
async def mail_settings_get(user: Annotated[dict, Depends(require_role("admin"))]):
    """Get current mail settings (without password)."""
    settings = _mail_get()
    if settings is None:
        return {"configured": False, "settings": None}
    return {"configured": True, "settings": settings}


@router.post("/api/settings/mail")
@limiter.limit("30/minute")
async def mail_settings_save(request: Request, body: MailSettingsUpdate, user: Annotated[dict, Depends(require_role("admin"))]):
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
async def mail_settings_test(request: Request, user: Annotated[dict, Depends(require_role("admin"))]):
    """Test SMTP connection with current settings."""
    return _mail_test()


@router.get("/api/settings/sms")
async def sms_settings_get(user: Annotated[dict, Depends(require_role("admin"))]):
    """Get current SMS settings."""
    settings = _sms_get()
    if settings is None:
        return {"configured": False, "settings": None}
    return {"configured": True, "settings": settings}


@router.post("/api/settings/sms")
@limiter.limit("30/minute")
async def sms_settings_save(request: Request, body: SMSSettingsUpdate, user: Annotated[dict, Depends(require_role("admin"))]):
    """Save SMS settings."""
    _sms_update(body.model_dump())
    return {"ok": True}


@router.post("/api/settings/sms/test")
@limiter.limit("10/minute")
async def sms_settings_test(request: Request, user: Annotated[dict, Depends(require_role("admin"))]):
    """Test SMS connection with current settings."""
    return _sms_test()


# ── Business Hours ─────────────────────────────────────────────────


@router.get("/api/settings/business-hours")
async def business_hours_get(user: Annotated[dict, Depends(require_role("admin", "tech", "front_desk"))]):
    """Get current business hours."""
    settings = _bh_get()
    if settings is None:
        return {"configured": False, "hours": DEFAULT_HOURS}
    return {"configured": True, "hours": settings}


@router.post("/api/settings/business-hours")
@limiter.limit("30/minute")
async def business_hours_save(request: Request, body: BusinessHoursUpdate, user: Annotated[dict, Depends(require_role("admin"))]):
    """Save business hours."""
    data = body.model_dump()
    result = _bh_update(data)
    return {"ok": True, "hours": result}
