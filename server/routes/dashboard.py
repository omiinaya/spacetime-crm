"""Dashboard stats + Reports + Audit Log routes."""
from __future__ import annotations

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException

from helpers import (
    _sql, _sql_t, _paginated, _call, _sort, _log_audit,
    require_role, get_current_user, logger,
)

router = APIRouter()


@router.get("/api/stats")
async def dashboard_stats(user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    all_customers = await _sql_t("SELECT * FROM customer", user["tenant_id"])
    all_tickets = await _sql_t("SELECT * FROM ticket", user["tenant_id"])
    all_invoices = await _sql_t("SELECT * FROM invoices", user["tenant_id"])
    all_appointments = await _sql_t("SELECT * FROM appointment", user["tenant_id"])
    total_customers = len(all_customers)
    total_tickets = len(all_tickets)
    open_tickets = sum(1 for t in all_tickets if t.get("status") not in ("resolved", "closed"))
    revenue = sum(float(i.get("total", 0)) for i in all_invoices if i.get("status") == "paid")
    pending_revenue = sum(float(i.get("total", 0)) for i in all_invoices if i.get("status") not in ("paid", "cancelled"))
    upcoming_appointments = sum(1 for a in all_appointments if a.get("start_time", 0) > 0)

    # Today's appointments
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    day_start_ms = int(datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
    day_end_ms = day_start_ms + 86400000
    today_appts = [a for a in all_appointments if day_start_ms <= a.get("start_time", 0) < day_end_ms and a.get("status") not in ("cancelled",)]
    today_appts_sorted = sorted(today_appts, key=lambda x: x.get("start_time", 0))[:10]

    # My assigned tickets for dashboard personalization
    my_tickets = [t for t in all_tickets if t.get("assigned_user_id") == user["id"] and t.get("status") not in ("resolved", "closed")]

    # Priority breakdown for my tickets
    my_ticket_counts = {"all": len(my_tickets), "urgent": 0, "high": 0, "medium": 0, "low": 0}
    for t in my_tickets:
        prio = t.get("priority", "medium")
        if prio in my_ticket_counts:
            my_ticket_counts[prio] += 1

    # Recent 5 my tickets for the dashboard card
    my_recent = sorted(my_tickets, key=lambda x: x.get("created_at", 0), reverse=True)[:5]

    return {
        "total_customers": total_customers,
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "revenue": revenue,
        "pending_revenue": pending_revenue,
        "upcoming_appointments": upcoming_appointments,
        "my_tickets": my_recent,
        "my_ticket_counts": my_ticket_counts,
        "today_appointments": today_appts_sorted,
    }


@router.get("/api/reports")
async def get_reports(user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """Reporting data for charts."""
    now = datetime.utcnow()
    all_tickets = await _sql_t("SELECT * FROM ticket", user["tenant_id"])
    all_invoices = await _sql_t("SELECT * FROM invoices", user["tenant_id"])
    all_payments = await _sql_t("SELECT * FROM payment", user["tenant_id"])
    all_appointments = await _sql_t("SELECT * FROM appointment", user["tenant_id"])

    # Revenue by month (last 12 months)
    revenue_by_month = []
    for i in range(11, -1, -1):
        month_start = datetime(now.year, now.month, 1) - timedelta(days=30 * i)
        month_start_ts = int(month_start.timestamp() * 1000)
        month_end_ts = int((month_start + timedelta(days=30)).timestamp() * 1000)
        month_label = month_start.strftime("%b %y")
        month_revenue = sum(
            float(p.get("amount", 0))
            for p in all_payments
            if month_start_ts <= p.get("created_at", 0) < month_end_ts
        )
        revenue_by_month.append({"month": month_label, "revenue": round(month_revenue, 2)})

    # Ticket counts by status
    status_counts: dict[str, int] = {}
    for t in all_tickets:
        s = t.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
    ticket_by_status = [{"status": s, "count": c} for s, c in sorted(status_counts.items())]

    # Invoice by status
    inv_status_counts: dict[str, int] = {}
    for inv in all_invoices:
        s = inv.get("status", "draft")
        inv_status_counts[s] = inv_status_counts.get(s, 0) + 1
    invoice_by_status = [{"status": s, "count": c} for s, c in sorted(inv_status_counts.items())]

    # Appointments by month (next 3 + past 9)
    appt_by_month = []
    for i in range(11, -1, -1):
        month_start = datetime(now.year, now.month, 1) - timedelta(days=30 * i)
        month_start_ts = int(month_start.timestamp() * 1000)
        month_end_ts = int((month_start + timedelta(days=30)).timestamp() * 1000)
        month_label = month_start.strftime("%b %y")
        month_count = sum(
            1 for a in all_appointments
            if month_start_ts <= a.get("start_time", 0) < month_end_ts
        )
        appt_by_month.append({"month": month_label, "appointments": month_count})

    total_revenue = sum(float(p.get("amount", 0)) for p in all_payments)
    total_tickets = len(all_tickets)
    open_tickets = sum(1 for t in all_tickets if t.get("status") not in ("resolved", "closed"))
    total_sent = sum(1 for inv in all_invoices if inv.get("status") not in ("draft", "cancelled"))
    total_paid = sum(1 for inv in all_invoices if inv.get("status") == "paid")
    outstanding_revenue = sum(
        float(inv.get("total", 0)) for inv in all_invoices
        if inv.get("status") in ("sent", "overdue", "partial")
    )

    resolution_times = []
    for t in all_tickets:
        created = t.get("created_at", 0)
        updated = t.get("updated_at", 0)
        if created and updated > created and t.get("status") in ("resolved", "closed"):
            resolution_times.append((updated - created) / (1000 * 3600))
    avg_resolution_hours = round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else 0

    tech_ticket_map: dict[str, int] = {}
    for t in all_tickets:
        uid = t.get("assigned_user_id", "")
        if uid and t.get("status") in ("resolved", "closed"):
            tech_ticket_map[uid] = tech_ticket_map.get(uid, 0) + 1
    all_users = await _sql("SELECT id, name FROM user")
    user_name_map = {u["id"]: u.get("name", "Unknown") for u in all_users}
    tech_closed = [
        {"user_name": user_name_map.get(uid, "Unknown"), "closed_count": count}
        for uid, count in sorted(tech_ticket_map.items(), key=lambda x: -x[1])
    ]

    customer_revenue: dict[str, float] = {}
    for inv in all_invoices:
        cid = inv.get("customer_id", "")
        if inv.get("status") == "paid":
            customer_revenue[cid] = customer_revenue.get(cid, 0) + float(inv.get("total", 0))
    all_customers = await _sql("SELECT id, first_name, last_name FROM customer")
    cust_name_map = {
        c["id"]: f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
        for c in all_customers
    }
    top_customers = [
        {"customer_name": cust_name_map.get(cid, "Unknown"), "revenue": round(rev, 2)}
        for cid, rev in sorted(customer_revenue.items(), key=lambda x: -x[1])[:10]
    ]

    return {
        "revenue_by_month": revenue_by_month,
        "ticket_by_status": ticket_by_status,
        "invoice_by_status": invoice_by_status,
        "appointments_by_month": appt_by_month,
        "totals": {
            "total_revenue": round(total_revenue, 2),
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "total_sent": total_sent,
            "total_paid": total_paid,
            "outstanding_revenue": round(outstanding_revenue, 2),
            "avg_resolution_hours": avg_resolution_hours,
        },
        "tech_closed": tech_closed,
        "top_customers": top_customers,
    }


# ── AUDIT LOG ──

@router.get("/api/audit-log")
async def get_audit_log(
    offset: int = 0,
    limit: int = 50,
    entity: str = "",
    action: str = "",
    user: dict = Depends(require_role("admin")),
):
    """Get audit log entries with pagination. Admin only."""
    where = ""
    if entity:
        where += f"entity = '{entity}'"
    if action:
        where += (" AND " if where else "") + f"action = '{action}'"
    rows, total = await _paginated(
        "", "audit_log",
        offset=offset, limit=limit,
        where_extra=where,
        order_by="created_at", order_desc=True,
    )
    return {"entries": rows, "total": total, "offset": offset, "limit": limit}
