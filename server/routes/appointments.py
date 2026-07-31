"""Appointment routes."""

from __future__ import annotations

import asyncio

from config import settings
from fastapi import APIRouter, Depends
from helpers import (
    _call,
    _fire_webhook,
    _log_audit,
    _paginated,
    _sql,
    _sqlesc,
    require_role,
)
from mail import (
    _customer_email as _mail_customer_email,
)
from mail import (
    _notify_appointment_created,
)
from mail import (
    _notify_appointment_reminder as _mail,
)
from models import (
    AppointmentCreate,
    AppointmentRecurrence,
    AppointmentStatusUpdate,
    GenerateNextOccurrence,
)
from sms import (
    _customer_phone as _sms_customer_phone,
)
from sms import (
    _notify_appointment_created as _sms_appointment_created,
)
from sms import (
    _notify_appointment_reminder as _sms,
)

router = APIRouter()

_RECURRENCE_INTERVALS: dict[str, int] = {
    "daily": 86_400_000,  # 24h
    "weekly": 604_800_000,  # 7d
    "biweekly": 1_209_600_000,  # 14d
    "monthly": 2_592_000_000,  # 30d (approx)
}


@router.get("/api/appointments")
async def list_appointments(
    customer_id: str = "",
    offset: int = 0,
    limit: int = 50,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """List appointments with pagination and optional customer filter."""
    conditions = []
    if customer_id:
        conditions.append(f"customer_id = '{_sqlesc(customer_id)}'")
    where = " AND ".join(conditions) if conditions else ""
    rows, total = await _paginated(
        user["tenant_id"],
        "appointment",
        offset=offset,
        limit=limit,
        order_by="start_time",
        order_desc=False,
        where_extra=where,
    )
    return {"appointments": rows, "total": total, "offset": offset, "limit": limit}


@router.get("/api/appointments/by-tech")
async def get_appointments_by_tech(
    start: int = 0,
    end: int = 0,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """Get appointments grouped by assigned tech for a time range."""
    tid = user["tenant_id"]

    rows = await _sql(
        f"SELECT * FROM appointment WHERE tenant_id = '{tid}' AND start_time >= {start} AND end_time <= {end} ORDER BY start_time"
    )

    # Fetch all users to resolve names
    user_rows = await _sql(f"SELECT id, name FROM user WHERE tenant_id = '{tid}'")
    user_map: dict[str, str] = {u["id"]: u["name"] for u in user_rows}

    # Fetch customers for appointment enrichment
    groups: dict[str, dict] = {}
    unassigned: list = []

    for appt in rows:
        uid = appt.get("assigned_user_id", "") or ""
        # Enrich with customer info
        if "customer" not in appt:
            cust = await _sql(
                f"SELECT first_name, last_name FROM customer WHERE id = '{appt.get('customer_id', '')}'"
            )
            appt["customer"] = cust[0] if cust else {}
        appt["customer_name"] = (
            f"{appt['customer'].get('first_name', '')} {appt['customer'].get('last_name', '')}".strip()
        )

        if uid:
            if uid not in groups:
                groups[uid] = {
                    "user_id": uid,
                    "user_name": user_map.get(uid, "Unknown"),
                    "appointments": [],
                }
            groups[uid]["appointments"].append(appt)
        else:
            unassigned.append(appt)

    return {
        "groups": list(groups.values()),
        "unassigned": unassigned,
    }


@router.get("/api/appointments/recurring")
async def list_recurring_series(
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """List recurring appointment series (parent appointments with recurrence_rule set)."""
    rows = await _sql(
        f"SELECT * FROM appointment WHERE tenant_id = '{user['tenant_id']}' AND recurrence_rule != '' AND series_id = ''"
    )
    series = []
    for s in rows:
        children = await _sql(
            f"SELECT * FROM appointment WHERE tenant_id = '{user['tenant_id']}' AND series_id = '{s['id']}'"
        )
        next_time = max([c["start_time"] for c in children]) if children else s["start_time"]
        series.append(
            {
                **s,
                "occurrence_count": len(children),
                "next_occurrence": next_time,
            }
        )
    return {"series": series}


@router.post("/api/appointments")
async def create_appointment(
    body: AppointmentCreate,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    await _call(
        "create_appointment",
        [
            user["tenant_id"],
            body.customer_id,
            body.ticket_id,
            body.title,
            body.description,
            body.start_time,
            body.end_time,
            body.all_day,
            body.series_id,
            body.recurrence_rule,
        ],
    )

    async def _notify():
        cust = await _sql(f"SELECT * FROM customer WHERE id = '{_sqlesc(body.customer_id)}'")
        email = _mail_customer_email(cust[0]) if cust else None
        if email:
            link = f"{settings.app_url}/portal/"
            _notify_appointment_created(email, body.title, body.start_time, link)
        phone = _sms_customer_phone(cust[0]) if cust else None
        if phone:
            _sms_appointment_created(phone, body.title, body.start_time)

    asyncio.ensure_future(_notify())

    await _log_audit(user, "create", "appointment", body.title)
    asyncio.ensure_future(
        _fire_webhook(
            "appointment.created",
            {
                "entity_type": "appointment",
                "title": body.title,
                "customer_id": body.customer_id,
                "start_time": body.start_time,
                "recurrence_rule": body.recurrence_rule,
            },
        )
    )
    return {"ok": True}


@router.put("/api/appointments/{appt_id}/recurrence")
async def set_appointment_recurrence(
    appt_id: str,
    body: AppointmentRecurrence,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """Set or update the recurrence rule on an appointment (makes it a series parent)."""
    await _call("set_recurrence", [appt_id, body.recurrence_rule])
    await _log_audit(
        user,
        "update_recurrence",
        "appointment",
        appt_id,
        f"rule={body.recurrence_rule}",
    )
    return {"ok": True}


@router.post("/api/appointments/generate-next")
async def generate_next_occurrence(
    body: GenerateNextOccurrence,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """Generate the next occurrence of a recurring appointment series."""
    # Find the parent series
    rows = await _sql(
        f"SELECT * FROM appointment WHERE tenant_id = '{user['tenant_id']}' AND id = '{body.series_id}' AND recurrence_rule != ''"
    )
    if not rows:
        return {"ok": False, "error": "Series not found"}
    parent = rows[0]

    rule = parent.get("recurrence_rule", "")
    interval_ms = _RECURRENCE_INTERVALS.get(rule)
    if not interval_ms:
        return {"ok": False, "error": f"Unknown recurrence rule: {rule}"}

    # Find the latest occurrence without ORDER BY (STDB limitation)
    children = await _sql(
        f"SELECT * FROM appointment WHERE tenant_id = '{user['tenant_id']}' AND series_id = '{body.series_id}'"
    )

    if children:
        # Manual sort — find the largest start_time
        latest = max(children, key=lambda c: c.get("start_time", 0))
        next_start = latest["start_time"] + interval_ms
        duration = latest["end_time"] - latest["start_time"]
        next_end = next_start + duration
    else:
        # No children yet — use the parent's time + one interval
        next_start = parent["start_time"] + interval_ms
        duration = parent["end_time"] - parent["start_time"]
        next_end = next_start + duration

    await _call("generate_next_occurrence", [body.series_id, next_start, next_end, rule])
    await _log_audit(
        user,
        "generate_occurrence",
        "appointment",
        body.series_id,
        f"start={next_start}",
    )
    return {"ok": True, "start_time": next_start, "end_time": next_end}


@router.get("/api/appointments/due-soon")
async def get_appointments_due_soon(
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """Get appointments starting in the next 24 hours."""
    now_ms = int(__import__("time").time() * 1000)
    in_24h = now_ms + 86_400_000  # 24h in ms

    rows = await _sql(
        f"SELECT * FROM appointment WHERE tenant_id = '{user['tenant_id']}' "
        f"AND status != 'cancelled' AND status != 'completed' "
        f"AND start_time >= {now_ms} AND start_time <= {in_24h}"
    )

    # Enrich with customer info
    result = sorted(rows, key=lambda r: r.get("start_time", 0))
    for r in result:
        cust = await _sql(
            f"SELECT first_name, last_name, email, mobile, phone FROM customer WHERE id = '{r.get('customer_id', '')}'"
        )
        r["customer"] = cust[0] if cust else {}

    return {"appointments": result, "count": len(result)}


@router.post("/api/appointments/send-reminders")
async def send_appointment_reminders(user: dict = Depends(require_role("admin"))):
    """Send reminder notifications for appointments starting in the next 24 hours."""
    now_ms = int(__import__("time").time() * 1000)
    in_24h = now_ms + 86_400_000

    rows = await _sql(
        f"SELECT * FROM appointment WHERE tenant_id = '{user['tenant_id']}' "
        f"AND status != 'cancelled' AND status != 'completed' "
        f"AND start_time >= {now_ms} AND start_time <= {in_24h}"
    )

    sent = {"email": 0, "sms": 0, "skipped": 0}
    for appt in rows:
        cust = await _sql(
            f"SELECT first_name, last_name, email, mobile, phone FROM customer WHERE id = '{appt.get('customer_id', '')}'"
        )
        if not cust:
            sent["skipped"] += 1
            continue

        c = cust[0]
        link = f"{settings.app_url}/portal/"

        email = c.get("email") or None
        if email:
            _mail(email, appt.get("title", "Appointment"), appt.get("start_time", 0), link)
            sent["email"] += 1

        phone = c.get("mobile") or c.get("phone") or None
        if phone:
            _sms(phone, appt.get("title", "Appointment"), appt.get("start_time", 0))
            sent["sms"] += 1

        if not email and not phone:
            sent["skipped"] += 1

    await _log_audit(
        user,
        "send_reminders",
        "appointment",
        f"{sent['email']} email, {sent['sms']} SMS, {sent['skipped']} skipped",
    )
    return {"ok": True, "sent": sent}


@router.put("/api/appointments/{appt_id}/status")
async def update_appointment_status(
    appt_id: str,
    body: AppointmentStatusUpdate,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    await _call("update_appointment_status", [appt_id, body.status])
    await _log_audit(user, "update_status", "appointment", appt_id, f"status={body.status}")
    return {"ok": True}


@router.delete("/api/appointments/{appt_id}")
async def delete_appointment(appt_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_appointment", [appt_id])
    await _log_audit(user, "delete", "appointment", appt_id)
    return {"ok": True}
