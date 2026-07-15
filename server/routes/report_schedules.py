"""Report schedule management — saved reports with scheduled email delivery."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from helpers import (
    _call,
    _log_audit,
    _safe_id,
    _sql,
    _sql_t,
    logger,
    require_role,
)
from mail import send_email
from rate_limit import limiter

from models.scheduled_reports import ScheduledReportCreate, ScheduledReportUpdate
from report_engine import calc_next_run, render_report_email

router = APIRouter()


# ── CRUD ──


@router.get("/api/report-schedules")
async def list_schedules(
    offset: int = 0,
    limit: int = 50,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """List all scheduled reports for this tenant."""
    rows = await _sql_t("SELECT * FROM scheduled_reports", user["tenant_id"])
    rows.sort(key=lambda r: r.get("next_run_at", 0))
    total = len(rows)
    return {"schedules": rows[offset : offset + limit], "total": total, "offset": offset, "limit": limit}


@router.post("/api/report-schedules")
async def create_schedule(body: ScheduledReportCreate, user: Annotated[dict, Depends(require_role("admin"))]):
    """Create a new scheduled report."""
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    next_run_at = calc_next_run(body.schedule_frequency, body.schedule_config, now_ms)

    result = await _call(
        "create_scheduled_report",
        [
            user["tenant_id"],
            body.name,
            body.report_type,
            body.schedule_frequency,
            json.dumps(body.schedule_config),
            json.dumps(body.recipients if isinstance(body.recipients, list) else [body.recipients]),
            json.dumps(body.filters),
            next_run_at,
        ],
    )

    await _log_audit(user, "create", "scheduled_report", "", body.name)
    return {"ok": True, "id": result.get("id", "") if isinstance(result, dict) else "", "next_run_at": next_run_at}


@router.put("/api/report-schedules/{schedule_id}")
async def update_schedule(
    schedule_id: str, body: ScheduledReportUpdate, user: Annotated[dict, Depends(require_role("admin"))]
):
    """Update an existing scheduled report."""
    _safe_id(schedule_id)
    existing = await _sql(f"SELECT * FROM scheduled_reports WHERE id = '{_safe_id(schedule_id)}'")
    if not existing:
        raise HTTPException(404, "Schedule not found")

    name = body.name
    report_type = body.report_type
    schedule_frequency = body.schedule_frequency
    enabled = body.enabled

    schedule_config = body.schedule_config
    recipients_raw = body.recipients
    filters = body.filters

    recipients = recipients_raw if isinstance(recipients_raw, list) else [recipients_raw]
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    next_run_at = calc_next_run(schedule_frequency, schedule_config, now_ms)

    await _call(
        "update_scheduled_report",
        [
            schedule_id,
            name,
            report_type,
            schedule_frequency,
            json.dumps(schedule_config),
            json.dumps(recipients),
            json.dumps(filters),
            next_run_at,
            enabled,
        ],
    )
    await _log_audit(user, "update", "scheduled_report", schedule_id, name)
    return {"ok": True}


@router.delete("/api/report-schedules/{schedule_id}")
async def delete_schedule(schedule_id: str, user: Annotated[dict, Depends(require_role("admin"))]):
    """Delete a scheduled report."""
    _safe_id(schedule_id)
    await _call("delete_scheduled_report", [schedule_id])
    await _log_audit(user, "delete", "scheduled_report", schedule_id)
    return {"ok": True}


# ── Run Now / Check Due ──


@router.post("/api/report-schedules/{schedule_id}/run-now")
async def run_schedule_now(schedule_id: str, user: Annotated[dict, Depends(require_role("admin", "tech"))]):
    """Generate and deliver a scheduled report immediately."""
    _safe_id(schedule_id)
    schedules = await _sql(f"SELECT * FROM scheduled_reports WHERE id = '{_safe_id(schedule_id)}'")
    if not schedules:
        raise HTTPException(404, "Schedule not found")

    return await _generate_and_deliver(schedules[0], user)


@router.get("/api/report-schedules/check-due")
async def check_due_schedules(user: Annotated[dict, Depends(require_role("admin"))]):
    """Find all enabled schedules past their next_run_at. Call from cron."""
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    all_rows = await _sql_t("SELECT * FROM scheduled_reports", user["tenant_id"])
    rows = [r for r in all_rows if r.get("enabled") and r.get("next_run_at", 0) <= now_ms]
    results = []
    for schedule in rows:
        result = await _generate_and_deliver(schedule, user)
        results.append({"id": schedule["id"], "name": schedule["name"], "result": result})
    return {"processed": len(results), "results": results}


# ── Internal helpers ──


async def _generate_and_deliver(schedule: dict, user: dict) -> dict:
    """Generate report data, render as HTML, and email to all recipients."""
    report_type = schedule.get("report_type", "revenue")
    recipients = json.loads(schedule.get("recipients_json", "[]") or "[]")
    filters = json.loads(schedule.get("filters_json", "{}") or "{}")
    tenant_id = schedule.get("tenant_id", user.get("tenant_id", ""))

    try:
        # 1. Generate report data
        report_data = await _build_report_data(report_type, tenant_id, filters)

        # 2. Render HTML email
        html = render_report_email(report_type, schedule.get("name", "Report"), report_data)

        # 3. Send to each recipient
        sent_count = 0
        errors = []
        for email in recipients:
            if not email or "@" not in email:
                continue
            try:
                ok = send_email(email, f"📊 Scheduled Report: {schedule.get('name', 'Report')}", html)
                if ok:
                    sent_count += 1
                else:
                    errors.append(f"Failed to send to {email}")
            except Exception as e:
                errors.append(f"{email}: {e}")

        # 4. Update schedule: mark as run, calculate next run
        now_ms = int(datetime.utcnow().timestamp() * 1000)
        next_run = calc_next_run(
            schedule.get("schedule_frequency", "daily"),
            json.loads(schedule.get("schedule_config_json", "{}") or "{}"),
            now_ms,
        )
        await _call("mark_report_run", [schedule["id"], next_run])

        return {"ok": True, "sent": sent_count, "total": len(recipients), "errors": errors}
    except Exception as e:
        logger.error("Report generation failed for %s: %s", schedule.get("name"), e)
        await _call("mark_report_error", [schedule["id"], str(e)[:500]])
        return {"ok": False, "error": str(e)}


async def _build_report_data(report_type: str, tenant_id: str, filters: dict) -> dict[str, Any]:
    """Query STDB and build report data for a given report type."""
    now = datetime.utcnow()

    def _filter_rows(rows: list[dict], field: str, value: Any) -> list[dict]:
        if not value:
            return rows
        return [r for r in rows if r.get(field) == value]

    if report_type == "revenue":
        payments = await _sql_t("SELECT * FROM payment", tenant_id)
        invoices = await _sql_t("SELECT * FROM invoices", tenant_id)
        period_start = filters.get("months_back", 12)

        revenue_by_month = []
        for i in range(period_start - 1, -1, -1):
            ms = datetime(now.year, now.month, 1) - timedelta(days=30 * i)
            ms_end = ms + timedelta(days=30)
            ms_ts = int(ms.timestamp() * 1000)
            ms_end_ts = int(ms_end.timestamp() * 1000)
            month_rev = sum(float(p.get("amount", 0)) for p in payments if ms_ts <= p.get("created_at", 0) < ms_end_ts)
            revenue_by_month.append({"label": ms.strftime("%b %y"), "value": round(month_rev, 2)})

        total_paid = sum(float(p.get("amount", 0)) for p in payments)
        total_sent = sum(1 for inv in invoices if inv.get("status") not in ("draft", "cancelled"))
        total_paid_count = sum(1 for inv in invoices if inv.get("status") == "paid")
        outstanding = sum(float(inv.get("total", 0)) for inv in invoices if inv.get("status") in ("sent", "overdue"))

        return {
            "metrics": [
                {"label": "Total Paid", "value": f"${total_paid:,.2f}"},
                {"label": "Invoices Sent", "value": total_sent},
                {"label": "Paid", "value": total_paid_count},
                {"label": "Outstanding", "value": f"${outstanding:,.2f}"},
            ],
            "chart_label": "Revenue by Month (Last {period_start} Months)",
            "chart": revenue_by_month,
        }

    elif report_type == "customers":
        customers = await _sql_t("SELECT * FROM customer", tenant_id)
        invoices = await _sql_t("SELECT * FROM invoices", tenant_id)
        tickets = await _sql_t("SELECT * FROM tickets", tenant_id)

        total_customers = len(customers)
        active = sum(1 for c in customers if c.get("active", True))
        invoices_open = sum(1 for inv in invoices if inv.get("status") in ("sent", "overdue", "partial"))
        tickets_open = sum(1 for t in tickets if t.get("status") == "open")

        top_customers = sorted(
            [
                {
                    "label": f"{c.get('first_name', '')} {c.get('last_name', '')}",
                    "value": sum(
                        float(inv.get("total", 0))
                        for inv in invoices
                        if inv.get("customer_id") == c.get("id") and inv.get("status") == "paid"
                    ),
                }
                for c in customers
            ],
            key=lambda x: x["value"],
            reverse=True,
        )[:10]

        return {
            "metrics": [
                {"label": "Total Customers", "value": total_customers},
                {"label": "Active", "value": active},
                {"label": "Open Invoices", "value": invoices_open},
                {"label": "Open Tickets", "value": tickets_open},
            ],
            "chart_label": "Top Customers by Revenue",
            "chart": top_customers,
        }

    elif report_type == "inventory":
        products = await _sql_t("SELECT * FROM products", tenant_id)
        low_stock = [p for p in products if p.get("quantity", 0) <= (p.get("low_stock_threshold", 5))]
        return {
            "metrics": [
                {"label": "Total Products", "value": len(products)},
                {"label": "Low Stock Items", "value": len(low_stock)},
            ],
            "chart_label": "Low Stock Items",
            "chart": [{"label": p.get("name", p.get("sku", "?")), "value": p.get("quantity", 0)} for p in low_stock],
        }

    elif report_type == "tickets":
        tickets = await _sql_t("SELECT * FROM tickets", tenant_id)
        status_counts = {}
        for t in tickets:
            s = t.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1
        return {
            "metrics": [
                {"label": "Total Tickets", "value": len(tickets)},
                {"label": "Open", "value": status_counts.get("open", 0)},
                {"label": "In Progress", "value": status_counts.get("in_progress", 0)},
                {"label": "Resolved", "value": status_counts.get("resolved", 0)},
            ],
            "chart_label": "Tickets by Status",
            "chart": [{"label": s, "value": c} for s, c in sorted(status_counts.items())],
        }

    else:
        return {
            "metrics": [{"label": "Report Type", "value": report_type}],
            "chart": [],
        }
