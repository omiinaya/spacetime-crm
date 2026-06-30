"""Ticket routes."""
from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends, HTTPException

from helpers import (
    _sql, _paginated, _call, _sort, _log_audit, _fire_webhook,
    require_role, logger,
)
from models import (
    TicketCreate, TicketStatusUpdate, TicketAssign, TicketNoteCreate, TicketTimerStart,
    ChecklistApply, ChecklistToggle,
)

router = APIRouter()


@router.get("/api/tickets")
async def list_tickets(status: str = "", offset: int = 0, limit: int = 50, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """List tickets with pagination and optional status filter."""
    where = f"status = '{status}'" if status else ""
    rows, total = await _paginated(
        user["tenant_id"], "ticket",
        offset=offset, limit=limit,
        where_extra=where,
        order_by="created_at", order_desc=True,
    )
    return {"tickets": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/api/tickets")
async def create_ticket(body: TicketCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("create_ticket", [
        user["tenant_id"],
        body.customer_id,
        body.title,
        body.description,
        body.device_type,
        body.device_model,
        body.device_serial,
        body.priority,
    ])
    await _log_audit(user, "create", "ticket", body.title, f"customer={body.customer_id}")
    asyncio.ensure_future(_fire_webhook("ticket.created", {
        "entity_type": "ticket",
        "title": body.title,
        "customer_id": body.customer_id,
    }))
    return {"ok": True}


@router.put("/api/tickets/{ticket_id}/status")
async def update_ticket_status(ticket_id: str, body: TicketStatusUpdate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    status = body.status
    await _call("update_ticket_status", [ticket_id, status])

    async def _notify():
        rows = await _sql(f"SELECT * FROM ticket WHERE id = '{ticket_id}'")
        if rows:
            t = rows[0]
            from mail import _customer_email as _mail_customer_email
            from mail import _notify_ticket_status_change
            cust = await _sql(f"SELECT * FROM customer WHERE id = '{t.get('customer_id', '')}'")
            email = _mail_customer_email(cust[0]) if cust else None
            if email:
                link = f"http://localhost:8723/portal/"
                _notify_ticket_status_change(email, t.get("ticket_number", 0), t.get("title", ""), status, link)
            from sms import _customer_phone as _sms_customer_phone
            from sms import _notify_ticket_status_change as _sms_ticket_status
            phone = _sms_customer_phone(cust[0]) if cust else None
            if phone:
                _sms_ticket_status(phone, t.get("ticket_number", 0), t.get("title", ""), status)
    asyncio.ensure_future(_notify())

    asyncio.ensure_future(_fire_webhook("ticket.status_changed", {
        "entity_type": "ticket",
        "id": ticket_id,
        "status": status,
    }))
    return {"ok": True}


@router.put("/api/tickets/{ticket_id}/assign")
async def assign_ticket(ticket_id: str, body: TicketAssign, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("assign_ticket", [ticket_id, body.assigned_user_id])
    await _log_audit(user, "assign", "ticket", ticket_id, f"user={body.assigned_user_id}")
    return {"ok": True}


@router.get("/api/tickets/{ticket_id}/notes")
async def get_ticket_notes(ticket_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql(f"SELECT * FROM ticket_note WHERE ticket_id = '{ticket_id}'")
    return {"notes": _sort(rows, "created_at", desc=False)}


@router.post("/api/tickets/{ticket_id}/notes")
async def add_ticket_note(ticket_id: str, body: TicketNoteCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("add_ticket_note", [
        ticket_id,
        body.author or user.get("name", ""),
        body.content,
        body.internal,
    ])
    await _log_audit(user, "add_note", "ticket", ticket_id)
    return {"ok": True}


@router.delete("/api/tickets/{ticket_id}")
async def delete_ticket(ticket_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_ticket", [ticket_id])
    await _log_audit(user, "delete", "ticket", ticket_id)
    return {"ok": True}


# ── TICKET TIMERS ──

@router.post("/api/tickets/{ticket_id}/timers/start")
async def start_ticket_timer(ticket_id: str, body: TicketTimerStart, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("start_ticket_timer", [ticket_id, body.user_id])
    rows = await _sql(f"SELECT * FROM ticket_timer WHERE ticket_id = '{ticket_id}'")
    return {"timers": _sort(rows, "start_time")}


@router.get("/api/timers")
async def list_all_timers(user_id: str = "", running: str = "", user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    query = "SELECT * FROM ticket_timer"
    filters = []
    if user_id:
        filters.append(f"user_id = '{user_id}'")
    if running == "true":
        filters.append("running = true")
    if filters:
        query += " WHERE " + " AND ".join(filters)
    rows = await _sql(query)
    return {"timers": _sort(rows, "start_time")}


@router.post("/api/timers/{timer_id}/stop")
async def stop_ticket_timer(timer_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("stop_ticket_timer", [timer_id])
    return {"ok": True}


@router.delete("/api/timers/{timer_id}")
async def delete_ticket_timer(timer_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_ticket_timer", [timer_id])
    await _log_audit(user, "delete", "timer", timer_id)
    return {"ok": True}


# ── TICKET CHECKLIST ──

@router.get("/api/tickets/{ticket_id}/checklist")
async def get_ticket_checklist(ticket_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """Get checklist items for a ticket."""
    rows = await _sql(f"SELECT * FROM ticket_checklist_items WHERE ticket_id = '{ticket_id}'")
    return {"items": _sort(rows, "sort_order")}


@router.post("/api/tickets/{ticket_id}/checklist/apply")
async def apply_checklist_to_ticket(ticket_id: str, body: ChecklistApply, user: dict = Depends(require_role("admin", "tech"))):
    """Apply a checklist template to a ticket."""
    await _call("apply_checklist_template", [ticket_id, body.template_id])
    await _log_audit(user, "apply", "checklist", ticket_id, f"template={body.template_id}")
    return {"ok": True}


@router.put("/api/tickets/{ticket_id}/checklist/{item_id}")
async def update_checklist_item(ticket_id: str, item_id: str, body: ChecklistToggle, user: dict = Depends(require_role("admin", "tech"))):
    """Toggle a checklist item completed/uncompleted."""
    await _call("update_checklist_item", [item_id, body.completed])
    return {"ok": True}


@router.delete("/api/tickets/{ticket_id}/checklist")
async def delete_ticket_checklist(ticket_id: str, user: dict = Depends(require_role("admin", "tech"))):
    """Remove all checklist items from a ticket."""
    await _call("delete_ticket_checklist", [ticket_id])
    await _log_audit(user, "delete", "checklist", ticket_id)
    return {"ok": True}


# ── TICKET SLA ──

SLA_TARGETS: dict[str, float] = {
    "urgent": 4,
    "high": 24,
    "medium": 72,
    "low": 120,
}


@router.get("/api/tickets/sla-breached")
async def list_sla_breaches(user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """List open tickets that have exceeded their SLA threshold."""
    now_ms = asyncio.get_event_loop().time() * 1000
    # Fetch all open tickets (STDB doesn't support NOT IN)
    open_statuses = ["new", "assigned", "in_progress", "waiting_on_customer"]
    all_open = []
    for status in open_statuses:
        rows, _ = await _paginated(
            user["tenant_id"], "ticket",
            offset=0, limit=1000,
            where_extra=f"status = '{status}'",
            order_by="created_at", order_desc=False,
        )
        all_open.extend(rows)
    breaches = []
    for t in all_open:
        target_hours = SLA_TARGETS.get(t.get("priority", "medium"), 72)
        created = t.get("created_at", 0)
        if not created:
            continue
        elapsed_hours = (now_ms - created) / 3_600_000
        if elapsed_hours > target_hours:
            breaches.append({
                "id": t["id"],
                "ticket_number": t.get("ticket_number", 0),
                "title": t.get("title", ""),
                "priority": t.get("priority", "medium"),
                "created_at": created,
                "elapsed_hours": round(elapsed_hours, 1),
                "target_hours": target_hours,
            })
    return {"breaches": breaches, "count": len(breaches)}


@router.get("/api/tickets/sla-targets")
async def get_sla_targets():
    """Return the current SLA threshold targets per priority."""
    return {"targets": SLA_TARGETS}
