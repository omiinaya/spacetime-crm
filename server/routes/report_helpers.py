"""Report helpers — data building, rendering, and delivery for scheduled reports."""

from __future__ import annotations

import json
from typing import Any

from helpers import _log_audit, _sql, _sqlesc, logger
from mail import send_email

from .report_schedules_helpers import _render_report_email


async def _generate_and_deliver(schedule: dict, user: dict) -> dict:
    """Generate report data, render as HTML, and email to all recipients."""
    report_type = schedule.get("report_type", "revenue")
    recipients = json.loads(schedule.get("recipients_json", "[]") or "[]")
    filters = json.loads(schedule.get("filters_json", "{}") or "{}")
    tenant_id = schedule.get("tenant_id", user.get("tenant_id", ""))

    try:
        # 1. Generate report data
        report_data = await _build_report_data(report_type, tenant_id, filters)
    except Exception as e:
        logger.error("Report generation failed: %s", e)
        await _log_audit(
            user,
            "error",
            "scheduled_report",
            schedule.get("id", ""),
            f"Generation failed: {e}",
        )
        return {"sent": 0, "failed": 0, "errors": [str(e)]}

    # 2. Render as HTML
    report_name = schedule.get("name", report_type.replace("_", " ").title())
    try:
        html = _render_report_email(report_type, report_name, report_data)
    except Exception as e:
        logger.error("Report rendering failed: %s", e)
        await _log_audit(
            user,
            "error",
            "scheduled_report",
            schedule.get("id", ""),
            f"Rendering failed: {e}",
        )
        return {"sent": 0, "failed": 0, "errors": [str(e)]}

    # 3. Email each recipient
    results = {"sent": 0, "failed": 0, "errors": []}
    for recipient in recipients:
        email_addr = recipient.get("email", "") if isinstance(recipient, dict) else recipient
        if not email_addr:
            continue
        try:
            await send_email(
                to=email_addr,
                subject=f"Scheduled Report: {report_name}",
                html_body=html,
            )
            results["sent"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append(str(e))
            logger.error("Failed to send report to %s: %s", email_addr, e)

    await _log_audit(
        user,
        "report_delivered",
        "scheduled_report",
        schedule.get("id", ""),
        f"Report '{report_name}' delivered to {results['sent']} recipient(s)",
    )
    return results


async def _build_report_data(report_type: str, tenant_id: str, filters: dict) -> dict[str, Any]:
    """Fetch and structure report data based on report type and optional filters.

    NOTE: STDB SQL supports no JOINs, no ORDER BY, and no bind params —
    all joining/sorting happens in Python.
    """
    if report_type == "revenue":
        rows = await _sql(
            f"SELECT total, created_at, status, customer_id FROM invoices "
            f"WHERE tenant_id = '{_sqlesc(tenant_id)}'"
        )
        rows.sort(key=lambda r: r.get("created_at", 0), reverse=True)
        customers = await _sql(
            f"SELECT id, first_name, last_name FROM customer WHERE tenant_id = '{_sqlesc(tenant_id)}'"
        )
        name_by_id = {
            c["id"]: f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
            for c in customers
        }
        decorated = [
            {
                "total": r.get("total"),
                "created_at": r.get("created_at"),
                "status": r.get("status"),
                "customer_name": name_by_id.get(r.get("customer_id", ""), ""),
            }
            for r in rows
        ]
        total_revenue = sum(
            float(r["total"] or 0) for r in decorated if r["status"] in ("paid", "sent")
        )
        period = filters.get("period", "all")
        return {
            "type": "revenue",
            "total_revenue": total_revenue,
            "invoice_count": len(decorated),
            "period": period,
            "rows": decorated[:50],
        }
    elif report_type == "tickets":
        rows = await _sql(
            f"SELECT ticket_number, title, status, priority, created_at, "
            f"customer_id FROM ticket WHERE tenant_id = '{_sqlesc(tenant_id)}'"
        )
        rows.sort(key=lambda r: r.get("created_at", 0), reverse=True)
        customers = await _sql(
            f"SELECT id, first_name, last_name FROM customer WHERE tenant_id = '{_sqlesc(tenant_id)}'"
        )
        name_by_id = {
            c["id"]: f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
            for c in customers
        }
        decorated = [
            {
                "ticket_number": r.get("ticket_number"),
                "title": r.get("title"),
                "status": r.get("status"),
                "priority": r.get("priority"),
                "created_at": r.get("created_at"),
                "customer_name": name_by_id.get(r.get("customer_id", ""), ""),
            }
            for r in rows
        ]
        status_filter = filters.get("status", "")
        if status_filter:
            decorated = _filter_rows(decorated, "status", status_filter)
        open_count = sum(
            1 for r in decorated if r.get("status", "") in ("new", "open", "in_progress")
        )
        return {
            "type": "tickets",
            "total": len(decorated),
            "open": open_count,
            "rows": decorated[:50],
        }
    elif report_type == "payments":
        rows = await _sql(
            f"SELECT amount, method, created_at, customer_id FROM payment "
            f"WHERE tenant_id = '{_sqlesc(tenant_id)}'"
        )
        rows.sort(key=lambda r: r.get("created_at", 0), reverse=True)
        customers = await _sql(
            f"SELECT id, first_name, last_name FROM customer WHERE tenant_id = '{_sqlesc(tenant_id)}'"
        )
        name_by_id = {
            c["id"]: f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
            for c in customers
        }
        decorated = [
            {
                "amount": r.get("amount"),
                "method": r.get("method"),
                "created_at": r.get("created_at"),
                "customer_name": name_by_id.get(r.get("customer_id", ""), ""),
            }
            for r in rows
        ]
        total_collected = sum(float(r.get("amount") or 0) for r in decorated)
        return {
            "type": "payments",
            "total_collected": total_collected,
            "payment_count": len(decorated),
            "rows": decorated[:50],
        }
    elif report_type in ("inventory", "products"):
        rows = await _sql(
            f"SELECT name, sku, quantity_on_hand, price, category FROM products "
            f"WHERE tenant_id = '{_sqlesc(tenant_id)}'"
        )
        rows.sort(key=lambda r: str(r.get("name", "")))
        low_stock = [
            r
            for r in rows
            if r.get("quantity_on_hand") is not None and (r.get("quantity_on_hand") or 0) < 5
        ]
        return {
            "type": report_type,
            "total_products": len(rows),
            "low_stock_count": len(low_stock),
            "rows": rows[:50],
        }
    else:
        return {"type": "unknown", "rows": []}


def _filter_rows(rows: list, field: str, value: str) -> list:
    """Filter rows where a field matches a value (case-insensitive)."""
    return [r for r in rows if str(r.get(field, "")).lower() == value.lower()]
