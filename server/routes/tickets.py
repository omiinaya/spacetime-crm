"""Ticket routes."""

from __future__ import annotations

import asyncio
import json
import time

from config import settings
from fastapi import APIRouter, Depends, HTTPException
from helpers import (
    _call,
    _fire_webhook,
    _log_audit,
    _paginated,
    _sort,
    _sql,
    logger,
    require_role,
)
from mail import _customer_email as _mail_customer_email
from mail import _notify_ticket_status_change
from models import (
    ChecklistApply,
    ChecklistToggle,
    TicketAssign,
    TicketCreate,
    TicketNoteCreate,
    TicketStatusUpdate,
    TicketTimerStart,
)
from push import send_notification_to_user
from sms import (
    _customer_phone as _sms_customer_phone,
)
from sms import (
    _notify_ticket_status_change as _sms_ticket_status,
)

router = APIRouter()


@router.get("/api/tickets")
async def list_tickets(
    status: str = "",
    customer_id: str = "",
    offset: int = 0,
    limit: int = 50,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """List tickets with pagination and optional status/customer filter."""
    conditions = []
    if status:
        conditions.append(f"status = '{status}'")
    if customer_id:
        conditions.append(f"customer_id = '{customer_id}'")
    where = " AND ".join(conditions) if conditions else ""
    rows, total = await _paginated(
        user["tenant_id"],
        "ticket",
        offset=offset,
        limit=limit,
        where_extra=where,
        order_by="created_at",
        order_desc=True,
    )
    return {"tickets": rows, "total": total, "offset": offset, "limit": limit}


# ── TICKET SLA (must be defined before {ticket_id} to avoid capture) ──

DEFAULT_SLA_TARGETS: dict[str, float] = {
    "urgent": 4,
    "high": 24,
    "medium": 72,
    "low": 120,
}


async def _load_sla_targets(tenant_id: str) -> dict[str, float]:
    """Load SLA targets from STDB sla_config, falling back to defaults."""
    rows = await _sql(f"SELECT * FROM sla_configs WHERE tenant_id = '{tenant_id}'")
    if rows:
        try:
            loaded = json.loads(rows[0]["targets_json"])
            # Merge with defaults so new or missing keys get a value
            merged: dict[str, float] = dict(DEFAULT_SLA_TARGETS)
            merged.update({k: float(v) for k, v in loaded.items() if isinstance(v, (int, float))})
            return merged
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    return dict(DEFAULT_SLA_TARGETS)


@router.get("/api/tickets/sla-breached")
async def list_sla_breaches(
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """List open tickets that have exceeded their SLA threshold."""
    targets = await _load_sla_targets(user["tenant_id"])
    now_ms = int(time.time() * 1000)
    # Fetch all open tickets (STDB doesn't support NOT IN)
    open_statuses = ["new", "assigned", "in_progress", "waiting_on_customer"]
    all_open = []
    for status in open_statuses:
        rows, _ = await _paginated(
            user["tenant_id"],
            "ticket",
            offset=0,
            limit=1000,
            where_extra=f"status = '{status}'",
            order_by="created_at",
            order_desc=False,
        )
        all_open.extend(rows)
    breaches = []
    for t in all_open:
        target_hours = targets.get(t.get("priority", "medium"), 72)
        created = t.get("created_at", 0)
        if not created:
            continue
        elapsed_hours = (now_ms - created) / 3_600_000
        if elapsed_hours > target_hours:
            breaches.append(
                {
                    "id": t["id"],
                    "ticket_number": t.get("ticket_number", 0),
                    "title": t.get("title", ""),
                    "priority": t.get("priority", "medium"),
                    "created_at": created,
                    "elapsed_hours": round(elapsed_hours, 1),
                    "target_hours": target_hours,
                }
            )
    return {"breaches": breaches, "count": len(breaches)}


@router.get("/api/tickets/sla-targets")
async def get_sla_targets(
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """Return the current SLA threshold targets per priority."""
    targets = await _load_sla_targets(user["tenant_id"])
    return {"targets": targets}


@router.get("/api/tickets/sla-settings")
async def get_sla_settings(user: dict = Depends(require_role("admin"))):
    """Get the full SLA config object from STDB."""
    tid = user["tenant_id"]
    rows = await _sql(f"SELECT * FROM sla_configs WHERE tenant_id = '{tid}'")
    if rows:
        return {
            "targets": json.loads(rows[0]["targets_json"]),
            "updated_at": rows[0].get("updated_at", 0),
        }
    return {"targets": DEFAULT_SLA_TARGETS, "updated_at": 0}


@router.post("/api/tickets/sla-settings")
async def save_sla_settings(
    body: dict,
    user: dict = Depends(require_role("admin")),
):
    """Save SLA thresholds. Expects {\"targets\": {\"urgent\": 4, \"high\": 24, ...}}."""
    targets = body.get("targets", {})
    # Validate: must have at least the 4 keys
    for key in ("urgent", "high", "medium", "low"):
        val = targets.get(key)
        if val is None or not isinstance(val, (int, float)) or val <= 0:
            raise HTTPException(400, f"Invalid or missing SLA target '{key}'")
        if val > 8760:  # 1 year
            raise HTTPException(400, f"SLA target '{key}' exceeds max (8760h)")
    targets_json = json.dumps(targets)
    await _call("upsert_sla_config", [user["tenant_id"], targets_json])
    # Expire cached SLA targets by returning fresh data
    fresh_targets = await _load_sla_targets(user["tenant_id"])
    return {"targets": fresh_targets, "ok": True}


@router.get("/api/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: str,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """Get a single ticket by ID."""
    rows = await _sql(
        f"SELECT * FROM ticket WHERE id = '{ticket_id}' AND tenant_id = '{user['tenant_id']}'"
    )
    if not rows:
        raise HTTPException(404, "Ticket not found")
    return {"ticket": rows[0]}


@router.post("/api/tickets")
async def create_ticket(
    body: TicketCreate,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    await _call(
        "create_ticket",
        [
            user["tenant_id"],
            body.customer_id,
            body.title,
            body.description,
            body.device_type,
            body.device_model,
            body.device_serial,
            body.priority,
        ],
    )
    await _log_audit(user, "create", "ticket", body.title, f"customer={body.customer_id}")
    asyncio.ensure_future(
        _fire_webhook(
            "ticket.created",
            {
                "entity_type": "ticket",
                "title": body.title,
                "customer_id": body.customer_id,
            },
        )
    )

    # Auto-assign to least-loaded staff member (admin or tech) if available
    try:
        tid = user["tenant_id"]
        # Find the most recently created ticket for this tenant
        recent = _sort(
            await _sql(f"SELECT id, status, created_at FROM ticket WHERE tenant_id = '{tid}'"),
            key="created_at",
        )
        if recent:
            new_id = recent[0]["id"]
            # Find staff (admin + tech) with fewest open tickets
            staff = await _sql(
                "SELECT id, name, role FROM \"user\" WHERE (role = 'admin' OR role = 'tech') AND active = true AND name != 'admin'"
            )
            if staff:
                # Count open tickets per staff member
                counts = []
                for s in staff:
                    open_tickets = await _sql(
                        f"SELECT COUNT(*) AS cnt FROM ticket WHERE assigned_user_id = '{s['id']}' AND status != 'resolved' AND status != 'closed' AND status != 'cancelled'"
                    )
                    cnt = int(open_tickets[0].get("cnt", 0)) if open_tickets else 0
                    counts.append((cnt, s["id"]))
                # Pick the one with fewest
                counts.sort()
                best_id = counts[0][1]
                await _call("assign_ticket", [new_id, best_id])
                logger.info(
                    "Auto-assigned ticket %s to user %s (%d open tickets)",
                    new_id[:12],
                    best_id,
                    counts[0][0],
                )
    except Exception as e:
        logger.warning("Auto-assign failed (non-fatal): %s", e)

    # Return the newly created ticket's ID
    recent = _sort(
        await _sql(f"SELECT id FROM ticket WHERE tenant_id = '{user['tenant_id']}'"),
        key="id",
    )
    new_id = recent[0]["id"] if recent else ""

    return {"ok": True, "id": new_id}


@router.put("/api/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: str,
    body: TicketStatusUpdate,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    status = body.status
    await _call("update_ticket_status", [ticket_id, status])

    async def _notify():
        rows = await _sql(f"SELECT * FROM ticket WHERE id = '{ticket_id}'")
        if rows:
            t = rows[0]
            cust = await _sql(f"SELECT * FROM customer WHERE id = '{t.get('customer_id', '')}'")
            email = _mail_customer_email(cust[0]) if cust else None
            if email:
                link = f"{settings.app_url}/portal/"
                _notify_ticket_status_change(
                    email, t.get("ticket_number", 0), t.get("title", ""), status, link
                )
            phone = _sms_customer_phone(cust[0]) if cust else None
            if phone:
                _sms_ticket_status(phone, t.get("ticket_number", 0), t.get("title", ""), status)
            # Push notification to assigned staff
            assigned_id = t.get("assigned_user_id", "")
            if assigned_id:
                asyncio.ensure_future(
                    send_notification_to_user(
                        assigned_id,
                        f"Ticket #{t.get('ticket_number', '')} {status}",
                        f"{t.get('title', '')[:80]} — status changed to {status}",
                        url="/",
                    )
                )

    asyncio.ensure_future(_notify())

    asyncio.ensure_future(
        _fire_webhook(
            "ticket.status_changed",
            {
                "entity_type": "ticket",
                "id": ticket_id,
                "status": status,
            },
        )
    )
    return {"ok": True}


@router.put("/api/tickets/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: str,
    body: TicketAssign,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    await _call("assign_ticket", [ticket_id, body.assigned_user_id])
    await _log_audit(user, "assign", "ticket", ticket_id, f"user={body.assigned_user_id}")
    return {"ok": True}


@router.get("/api/tickets/{ticket_id}/notes")
async def get_ticket_notes(
    ticket_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))
):
    rows = await _sql(f"SELECT * FROM ticket_note WHERE ticket_id = '{ticket_id}'")
    return {"notes": _sort(rows, "created_at", desc=False)}


@router.post("/api/tickets/{ticket_id}/notes")
async def add_ticket_note(
    ticket_id: str,
    body: TicketNoteCreate,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    await _call(
        "add_ticket_note",
        [
            ticket_id,
            body.author or user.get("name", ""),
            body.content,
            body.internal,
        ],
    )
    await _log_audit(user, "add_note", "ticket", ticket_id)
    return {"ok": True}


@router.delete("/api/tickets/{ticket_id}")
async def delete_ticket(ticket_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_ticket", [ticket_id])
    await _log_audit(user, "delete", "ticket", ticket_id)
    return {"ok": True}


# ── TICKET TIMERS ──


@router.post("/api/tickets/{ticket_id}/timers/start")
async def start_ticket_timer(
    ticket_id: str,
    body: TicketTimerStart,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    await _call("start_ticket_timer", [ticket_id, body.user_id])
    rows = await _sql(f"SELECT * FROM ticket_timer WHERE ticket_id = '{ticket_id}'")
    return {"timers": _sort(rows, "start_time")}


@router.get("/api/timers")
async def list_all_timers(
    user_id: str = "",
    running: str = "",
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
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
async def stop_ticket_timer(
    timer_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))
):
    await _call("stop_ticket_timer", [timer_id])
    return {"ok": True}


@router.delete("/api/timers/{timer_id}")
async def delete_ticket_timer(timer_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_ticket_timer", [timer_id])
    await _log_audit(user, "delete", "timer", timer_id)
    return {"ok": True}


# ── TICKET CHECKLIST ──


@router.get("/api/tickets/{ticket_id}/checklist")
async def get_ticket_checklist(
    ticket_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))
):
    """Get checklist items for a ticket."""
    rows = await _sql(f"SELECT * FROM ticket_checklist_items WHERE ticket_id = '{ticket_id}'")
    return {"items": _sort(rows, "sort_order")}


@router.post("/api/tickets/{ticket_id}/checklist/apply")
async def apply_checklist_to_ticket(
    ticket_id: str,
    body: ChecklistApply,
    user: dict = Depends(require_role("admin", "tech")),
):
    """Apply a checklist template to a ticket."""
    await _call("apply_checklist_template", [ticket_id, body.template_id])
    await _log_audit(user, "apply", "checklist", ticket_id, f"template={body.template_id}")
    return {"ok": True}


@router.put("/api/tickets/{ticket_id}/checklist/{item_id}")
async def update_checklist_item(
    ticket_id: str,
    item_id: str,
    body: ChecklistToggle,
    user: dict = Depends(require_role("admin", "tech")),
):
    """Toggle a checklist item completed/uncompleted."""
    await _call("update_checklist_item", [item_id, body.completed])
    return {"ok": True}


@router.delete("/api/tickets/{ticket_id}/checklist")
async def delete_ticket_checklist(
    ticket_id: str, user: dict = Depends(require_role("admin", "tech"))
):
    """Remove all checklist items from a ticket."""
    await _call("delete_ticket_checklist", [ticket_id])
    await _log_audit(user, "delete", "checklist", ticket_id)
    return {"ok": True}
