"""Appointment routes."""
from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends

from helpers import (
    _sql, _paginated, _call, _log_audit, _fire_webhook,
    require_role, logger,
)
from models import AppointmentCreate, AppointmentStatusUpdate

router = APIRouter()


@router.get("/api/appointments")
async def list_appointments(offset: int = 0, limit: int = 50, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """List appointments with pagination."""
    rows, total = await _paginated(
        user["tenant_id"], "appointment",
        offset=offset, limit=limit,
        order_by="start_time", order_desc=False,
    )
    return {"appointments": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/api/appointments")
async def create_appointment(body: AppointmentCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("create_appointment", [
        user["tenant_id"],
        body.customer_id,
        body.ticket_id,
        body.title,
        body.description,
        body.start_time,
        body.end_time,
        body.all_day,
    ])

    async def _notify():
        cust = await _sql(f"SELECT * FROM customer WHERE id = '{body.customer_id}'")
        from mail import _customer_email as _mail_customer_email
        from mail import _notify_appointment_created
        from sms import _customer_phone as _sms_customer_phone
        from sms import _notify_appointment_created as _sms_appointment_created
        email = _mail_customer_email(cust[0]) if cust else None
        if email:
            link = f"http://localhost:8723/portal/"
            _notify_appointment_created(email, body.title, body.start_time, link)
        phone = _sms_customer_phone(cust[0]) if cust else None
        if phone:
            _sms_appointment_created(phone, body.title, body.start_time)
    asyncio.ensure_future(_notify())

    await _log_audit(user, "create", "appointment", body.title)
    asyncio.ensure_future(_fire_webhook("appointment.created", {
        "entity_type": "appointment",
        "title": body.title,
        "customer_id": body.customer_id,
        "start_time": body.start_time,
    }))
    return {"ok": True}


@router.put("/api/appointments/{appt_id}/status")
async def update_appointment_status(appt_id: str, body: AppointmentStatusUpdate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("update_appointment_status", [appt_id, body.status])
    await _log_audit(user, "update_status", "appointment", appt_id, f"status={body.status}")
    return {"ok": True}


@router.delete("/api/appointments/{appt_id}")
async def delete_appointment(appt_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_appointment", [appt_id])
    await _log_audit(user, "delete", "appointment", appt_id)
    return {"ok": True}
