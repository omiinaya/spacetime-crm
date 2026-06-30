"""Report schedule management — saved reports with scheduled email delivery."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException

from helpers import (
    _sql, _sql_t, _call, _log_audit,
    require_role, _safe_id, logger,
)

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
    return {"schedules": rows[offset:offset + limit], "total": total, "offset": offset, "limit": limit}


@router.post("/api/report-schedules")
async def create_schedule(body: dict, user: dict = Depends(require_role("admin"))):
    """Create a new scheduled report."""
    required = ["name", "report_type", "schedule_frequency", "recipients"]
    for field in required:
        if field not in body:
            raise HTTPException(400, f"Missing required field: {field}")

    valid_types = ["revenue", "tickets", "invoices", "appointments", "tech_productivity", "customers"]
    if body["report_type"] not in valid_types:
        raise HTTPException(400, f"Invalid report_type. Valid: {', '.join(valid_types)}")

    valid_freq = ["daily", "weekly", "monthly"]
    if body["schedule_frequency"] not in valid_freq:
        raise HTTPException(400, f"Invalid schedule_frequency. Valid: {', '.join(valid_freq)}")

    now_ms = int(datetime.utcnow().timestamp() * 1000)
    next_run_at = _calc_next_run(body["schedule_frequency"], body.get("schedule_config", {}), now_ms)

    result = await _call("create_scheduled_report", [
        user["tenant_id"],
        body["name"],
        body["report_type"],
        body["schedule_frequency"],
        json.dumps(body.get("schedule_config", {})),
        json.dumps(body["recipients"] if isinstance(body["recipients"], list) else [body["recipients"]]),
        json.dumps(body.get("filters", {})),
        next_run_at,
    ])

    await _log_audit(user, "create", "scheduled_report", "", body["name"])
    return {"ok": True, "id": result.get("id", "") if isinstance(result, dict) else "", "next_run_at": next_run_at}


@router.put("/api/report-schedules/{schedule_id}")
async def update_schedule(schedule_id: str, body: dict, user: dict = Depends(require_role("admin"))):
    """Update an existing scheduled report."""
    _safe_id(schedule_id)
    existing = await _sql(f"SELECT * FROM scheduled_reports WHERE id = '{schedule_id}'")
    if not existing:
        raise HTTPException(404, "Schedule not found")

    name = body.get("name", existing[0].get("name", ""))
    report_type = body.get("report_type", existing[0].get("report_type", ""))
    schedule_frequency = body.get("schedule_frequency", existing[0].get("schedule_frequency", ""))
    enabled = body.get("enabled", existing[0].get("enabled", True))

    schedule_config = body.get("schedule_config", json.loads(existing[0].get("schedule_config_json", "{}") or "{}"))
    recipients_raw = body.get("recipients", json.loads(existing[0].get("recipients_json", "[]") or "[]"))
    filters = body.get("filters", json.loads(existing[0].get("filters_json", "{}") or "{}"))

    recipients = recipients_raw if isinstance(recipients_raw, list) else [recipients_raw]
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    next_run_at = body.get("next_run_at", _calc_next_run(schedule_frequency, schedule_config, now_ms))

    await _call("update_scheduled_report", [
        schedule_id, name, report_type, schedule_frequency,
        json.dumps(schedule_config), json.dumps(recipients),
        json.dumps(filters), next_run_at, enabled,
    ])
    await _log_audit(user, "update", "scheduled_report", schedule_id, name)
    return {"ok": True}


@router.delete("/api/report-schedules/{schedule_id}")
async def delete_schedule(schedule_id: str, user: dict = Depends(require_role("admin"))):
    """Delete a scheduled report."""
    _safe_id(schedule_id)
    await _call("delete_scheduled_report", [schedule_id])
    await _log_audit(user, "delete", "scheduled_report", schedule_id)
    return {"ok": True}


# ── Run Now / Check Due ──


@router.post("/api/report-schedules/{schedule_id}/run-now")
async def run_schedule_now(schedule_id: str, user: dict = Depends(require_role("admin", "tech"))):
    """Generate and deliver a scheduled report immediately."""
    _safe_id(schedule_id)
    schedules = await _sql(f"SELECT * FROM scheduled_reports WHERE id = '{schedule_id}'")
    if not schedules:
        raise HTTPException(404, "Schedule not found")

    result = await _generate_and_deliver(schedules[0], user)
    return result


@router.get("/api/report-schedules/check-due")
async def check_due_schedules(user: dict = Depends(require_role("admin"))):
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
        html = _render_report_email(report_type, schedule.get("name", "Report"), report_data)

        # 3. Send to each recipient
        sent_count = 0
        errors = []
        for email in recipients:
            if not email or "@" not in email:
                continue
            try:
                from mail import send_email
                ok = send_email(email, f"📊 Scheduled Report: {schedule.get('name', 'Report')}", html)
                if ok:
                    sent_count += 1
                else:
                    errors.append(f"Failed to send to {email}")
            except Exception as e:
                errors.append(f"{email}: {e}")

        # 4. Update schedule: mark as run, calculate next run
        now_ms = int(datetime.utcnow().timestamp() * 1000)
        next_run = _calc_next_run(
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


def _calc_next_run(frequency: str, config: dict, from_ms: int) -> int:
    """Calculate the next run timestamp based on frequency and config."""
    dt = datetime.fromtimestamp(from_ms / 1000)
    hour = config.get("hour", 8)
    minute = config.get("minute", 0)

    if frequency == "daily":
        next_dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_dt <= dt:
            next_dt += timedelta(days=1)
    elif frequency == "weekly":
        day_of_week = config.get("day_of_week", 0)  # 0=Monday
        next_dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
        days_ahead = (day_of_week - next_dt.weekday()) % 7
        if days_ahead == 0 and next_dt <= dt:
            days_ahead = 7
        next_dt += timedelta(days=days_ahead)
    elif frequency == "monthly":
        day_of_month = min(config.get("day_of_month", 1), 28)
        next_dt = dt.replace(day=day_of_month, hour=hour, minute=minute, second=0, microsecond=0)
        if next_dt <= dt:
            if next_dt.month == 12:
                next_dt = next_dt.replace(year=next_dt.year + 1, month=1)
            else:
                next_dt = next_dt.replace(month=next_dt.month + 1)
    else:
        next_dt = dt + timedelta(days=1)

    return int(next_dt.timestamp() * 1000)


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
            month_rev = sum(
                float(p.get("amount", 0))
                for p in payments
                if ms_ts <= p.get("created_at", 0) < ms_end_ts
            )
            revenue_by_month.append({"label": ms.strftime("%b %y"), "value": round(month_rev, 2)})

        total_paid = sum(float(p.get("amount", 0)) for p in payments)
        total_sent = sum(1 for inv in invoices if inv.get("status") not in ("draft", "cancelled"))
        total_paid_count = sum(1 for inv in invoices if inv.get("status") == "paid")
        outstanding = sum(
            float(inv.get("total", 0)) for inv in invoices
            if inv.get("status") in ("sent", "overdue", "partial")
        )

        return {
            "title": "Revenue Report",
            "metrics": [
                {"label": "Total Revenue", "value": f"${total_paid:,.2f}"},
                {"label": "Outstanding", "value": f"${outstanding:,.2f}"},
                {"label": "Invoices Sent", "value": str(total_sent)},
                {"label": "Invoices Paid", "value": str(total_paid_count)},
            ],
            "chart": revenue_by_month,
            "chart_label": "Revenue by Month",
        }

    elif report_type == "tickets":
        tickets = await _sql_t("SELECT * FROM ticket", tenant_id)
        status_filter = filters.get("status", "")
        if status_filter:
            tickets = _filter_rows(tickets, "status", status_filter)

        status_counts: dict[str, int] = {}
        for t in tickets:
            s = t.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1
        ticket_by_status = [{"label": s.capitalize(), "value": c} for s, c in sorted(status_counts.items())]

        open_count = sum(1 for t in tickets if t.get("status") not in ("resolved", "closed"))
        resolved_count = sum(1 for t in tickets if t.get("status") in ("resolved", "closed"))
        total_tickets = len(tickets)

        resolution_times = []
        for t in tickets:
            created = t.get("created_at", 0)
            updated = t.get("updated_at", 0)
            if created and updated > created and t.get("status") in ("resolved", "closed"):
                resolution_times.append((updated - created) / (1000 * 3600))
        avg_resolution = round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else 0

        # Tech productivity
        tech_counts: dict[str, int] = {}
        for t in tickets:
            uid = t.get("assigned_user_id", "")
            if uid and t.get("status") in ("resolved", "closed"):
                tech_counts[uid] = tech_counts.get(uid, 0) + 1
        all_users = await _sql("SELECT id, name FROM user")
        user_name_map = {u["id"]: u.get("name", "Unknown") for u in all_users}
        tech_closed = [
            {"label": user_name_map.get(uid, "Unknown"), "value": c}
            for uid, c in sorted(tech_counts.items(), key=lambda x: -x[1])
        ]

        return {
            "title": "Tickets Report",
            "metrics": [
                {"label": "Total Tickets", "value": str(total_tickets)},
                {"label": "Open", "value": str(open_count)},
                {"label": "Resolved/Closed", "value": str(resolved_count)},
                {"label": "Avg Resolution", "value": f"{avg_resolution}h"},
            ],
            "chart": ticket_by_status,
            "chart_label": "Tickets by Status",
            "chart2": tech_closed,
            "chart2_label": "Tech Productivity (Closed)",
        }

    elif report_type == "invoices":
        invoices = await _sql_t("SELECT * FROM invoices", tenant_id)
        status_filter = filters.get("status", "")
        if status_filter:
            invoices = _filter_rows(invoices, "status", status_filter)

        status_counts: dict[str, int] = {}
        total_rev = 0.0
        for inv in invoices:
            s = inv.get("status", "draft")
            status_counts[s] = status_counts.get(s, 0) + 1
            if inv.get("status") == "paid":
                total_rev += float(inv.get("total", 0))

        inv_by_status = [{"label": s.capitalize(), "value": c} for s, c in sorted(status_counts.items())]
        outstanding = sum(
            float(inv.get("total", 0)) for inv in invoices
            if inv.get("status") in ("sent", "overdue", "partial")
        )

        return {
            "title": "Invoice Report",
            "metrics": [
                {"label": "Total Invoices", "value": str(len(invoices))},
                {"label": "Total Collected", "value": f"${total_rev:,.2f}"},
                {"label": "Outstanding", "value": f"${outstanding:,.2f}"},
                {"label": "Overdue", "value": str(status_counts.get("overdue", 0))},
            ],
            "chart": inv_by_status,
            "chart_label": "Invoices by Status",
        }

    elif report_type == "appointments":
        appointments = await _sql_t("SELECT * FROM appointment", tenant_id)

        appt_by_month = []
        for i in range(11, -1, -1):
            ms = datetime(now.year, now.month, 1) - timedelta(days=30 * i)
            ms_end = ms + timedelta(days=30)
            ms_ts = int(ms.timestamp() * 1000)
            ms_end_ts = int(ms_end.timestamp() * 1000)
            appt_by_month.append({
                "label": ms.strftime("%b %y"),
                "value": sum(1 for a in appointments if ms_ts <= a.get("start_time", 0) < ms_end_ts),
            })

        status_counts: dict[str, int] = {}
        for a in appointments:
            s = a.get("status", "scheduled")
            status_counts[s] = status_counts.get(s, 0) + 1

        return {
            "title": "Appointments Report",
            "metrics": [
                {"label": "Total Appointments", "value": str(len(appointments))},
                {"label": "Completed", "value": str(status_counts.get("completed", 0))},
                {"label": "Cancelled", "value": str(status_counts.get("cancelled", 0))},
                {"label": "No-Show", "value": str(status_counts.get("no_show", 0))},
            ],
            "chart": appt_by_month,
            "chart_label": "Appointments by Month",
        }

    elif report_type == "tech_productivity":
        tickets = await _sql_t("SELECT * FROM ticket", tenant_id)
        all_users = await _sql("SELECT id, name FROM user")
        user_name_map = {u["id"]: u.get("name", "Unknown") for u in all_users}

        # Tech productivity
        tech_data_map: dict[str, dict[str, Any]] = {}
        for t in tickets:
            uid = t.get("assigned_user_id", "")
            if not uid:
                continue
            if uid not in tech_data_map:
                tech_data_map[uid] = {"assigned": 0, "resolved": 0, "hours": 0.0}
            tech_data_map[uid]["assigned"] += 1
            if t.get("status") in ("resolved", "closed"):
                tech_data_map[uid]["resolved"] += 1
            created = t.get("created_at", 0)
            updated = t.get("updated_at", 0)
            if created and updated > created and t.get("status") in ("resolved", "closed"):
                tech_data_map[uid]["hours"] += (updated - created) / (1000 * 3600)

        tech_data = [
            {
                "label": user_name_map.get(uid, "Unknown"),
                "value": d["resolved"],
                "extra": f"{d['assigned']} assigned, {d['hours']:.1f}h avg",
            }
            for uid, d in sorted(tech_data_map.items(), key=lambda x: -x[1]["resolved"])
        ]

        total_resolved = sum(d["resolved"] for d in tech_data_map.values())
        total_assigned = sum(d["assigned"] for d in tech_data_map.values())

        return {
            "title": "Tech Productivity Report",
            "metrics": [
                {"label": "Total Tickets", "value": str(total_assigned)},
                {"label": "Resolved/Closed", "value": str(total_resolved)},
                {"label": "Resolution Rate", "value": f"{round(total_resolved / total_assigned * 100, 1) if total_assigned else 0}%"},
                {"label": "Active Techs", "value": str(len(tech_counts))},
            ],
            "chart": tech_data,
            "chart_label": "Tickets Closed by Tech",
        }

    elif report_type == "customers":
        customers = await _sql_t("SELECT * FROM customer", tenant_id)
        invoices = await _sql_t("SELECT * FROM invoices", tenant_id)

        customer_revenue: dict[str, float] = {}
        for inv in invoices:
            cid = inv.get("customer_id", "")
            if inv.get("status") == "paid":
                customer_revenue[cid] = customer_revenue.get(cid, 0) + float(inv.get("total", 0))

        top_customers = [
            {
                "label": c.get("first_name", "") + " " + c.get("last_name", ""),
                "value": round(customer_revenue.get(c["id"], 0), 2),
            }
            for c in customers
        ]
        top_customers.sort(key=lambda x: -x["value"])

        return {
            "title": "Customer Report",
            "metrics": [
                {"label": "Total Customers", "value": str(len(customers))},
                {"label": "Active (with invoices)", "value": str(len(set(inv.get("customer_id", "") for inv in invoices)))},
                {"label": "Avg Revenue/Customer", "value": f"${round(sum(customer_revenue.values()) / len(customer_revenue), 2) if customer_revenue else 0}"},
            ],
            "chart": top_customers[:10],
            "chart_label": "Top Customers by Revenue",
        }

    return {"title": "Unknown Report", "metrics": [], "chart": [], "chart_label": ""}


def _render_report_email(report_type: str, name: str, data: dict) -> str:
    """Render report data as an HTML email."""
    metrics_html = "".join(
        f'<tr><td style="padding:8px 16px;border-bottom:1px solid #eee;color:#666">{m["label"]}</td>'
        f'<td style="padding:8px 16px;border-bottom:1px solid #eee;font-weight:bold;text-align:right">{m["value"]}</td></tr>'
        for m in data.get("metrics", [])
    )

    chart_html = ""
    if data.get("chart"):
        max_val = max((c["value"] for c in data["chart"]), default=1) or 1
        bars = "".join(
            f'<div style="display:flex;align-items:center;margin:4px 0">'
            f'<span style="width:80px;font-size:11px;color:#666;text-align:right;padding-right:8px">{c["label"]}</span>'
            f'<div style="flex:1;background:#f0f0f0;border-radius:4px;overflow:hidden;height:20px">'
            f'<div style="width:{max(c["value"] / max_val * 100, 5)}%;background:#6366f1;height:20px;border-radius:4px;text-align:right;padding-right:4px;line-height:20px;font-size:10px;color:#fff;min-width:fit-content">'
            f'{c["value"]}</div></div></div>'
            for c in data["chart"]
        )
        chart_html = f'<h3 style="color:#333;margin:20px 0 10px">{data.get("chart_label", "")}</h3>{bars}'

    chart2_html = ""
    if data.get("chart2"):
        max_val = max((c["value"] for c in data["chart2"]), default=1) or 1
        bars2 = "".join(
            f'<div style="display:flex;align-items:center;margin:4px 0">'
            f'<span style="width:120px;font-size:11px;color:#666;text-align:right;padding-right:8px">{c["label"]}</span>'
            f'<div style="flex:1;background:#f0f0f0;border-radius:4px;overflow:hidden;height:20px">'
            f'<div style="width:{max(c["value"] / max_val * 100, 5)}%;background:#22c55e;height:20px;border-radius:4px;text-align:right;padding-right:4px;line-height:20px;font-size:10px;color:#fff">'
            f'{c["value"]}</div></div></div>'
            for c in data["chart2"]
        )
        chart2_html = f'<h3 style="color:#333;margin:20px 0 10px">{data.get("chart2_label", "")}</h3>{bars2}'

    extra_html = ""
    if data.get("chart2"):
        extra = data["chart2"][0].get("extra", "") if data["chart2"] else ""
        if extra:
            extra_html = f'<p style="color:#999;font-size:11px">{extra}</p>'

    return f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:640px;margin:0 auto;padding:20px;background:#f9fafb">
<div style="background:#fff;border-radius:12px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,.1)">
<h1 style="font-size:20px;color:#111;margin:0 0 4px">📊 {data.get("title", name)}</h1>
<p style="color:#666;font-size:13px;margin:0 0 20px">{datetime.utcnow().strftime("%B %d, %Y")}</p>

<table style="width:100%;border-collapse:collapse;margin:16px 0;background:#f8f8ff;border-radius:8px">{metrics_html}</table>

{chart_html}
{chart2_html}
{extra_html}

<p style="color:#999;font-size:11px;margin-top:24px;text-align:center">
SpacetimeCRM · Automated Report Delivery
</p>
</div></body></html>"""
