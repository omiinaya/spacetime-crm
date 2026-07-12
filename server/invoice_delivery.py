"""Invoice delivery helpers — email/SMS notification, status utilities.

Extracted from routes/invoices.py for better testability and reuse.
"""

from __future__ import annotations

from typing import Any, Callable


# ── Invoice Status Utilities ──

INVOICE_STATUSES = [
    "draft",
    "sent",
    "paid",
    "partial",
    "overdue",
    "cancelled",
]

STATUS_CSS: dict[str, str] = {
    "draft": "#9ca3af",
    "sent": "#f59e0b",
    "paid": "#10b981",
    "partial": "#3b82f6",
    "overdue": "#ef4444",
    "cancelled": "#6b7280",
}

STATUS_LABELS: dict[str, str] = {
    "draft": "Draft",
    "sent": "Sent",
    "paid": "Paid",
    "partial": "Partial",
    "overdue": "Overdue",
    "cancelled": "Cancelled",
}


def build_invoice_data(inv: dict) -> dict:
    """Extract and normalize invoice fields into a clean dictionary."""
    return {
        "id": inv.get("id", ""),
        "number": inv.get("invoice_number", ""),
        "total": float(inv.get("total", 0)),
        "status": inv.get("status", "unknown"),
        "customer_id": inv.get("customer_id", ""),
        "due_date": inv.get("due_date", 0),
        "created_at": inv.get("created_at", 0),
        "currency": inv.get("currency", "USD"),
    }


async def send_invoice_notification(
    email: str,
    phone: str,
    invoice_number: int | str,
    total: float,
    portal_link: str = "",
    send_email_func: Callable | None = None,
    send_sms_func: Callable | None = None,
) -> dict:
    """Send invoice notification via email and/or SMS.

    Returns dict with "email" and "sms" booleans indicating which channels sent.
    """
    result = {"email": False, "sms": False}

    if email and send_email_func:
        try:
            send_email_func(email, invoice_number, total, portal_link)
            result["email"] = True
        except Exception:
            pass

    if phone and send_sms_func:
        try:
            send_sms_func(phone, invoice_number, total)
            result["sms"] = True
        except Exception:
            pass

    return result


async def send_batch_notifications(
    invoices: list[dict],
    send_email_func: Callable | None = None,
    send_sms_func: Callable | None = None,
) -> dict:
    """Send notifications for a batch of invoices.

    Each invoice dict should have: id, invoice_number, total,
    customer_email, customer_phone.

    Returns dict with sent/failed/skipped counts and details.
    """
    results = {"sent": 0, "failed": 0, "skipped": 0, "details": []}

    for inv in invoices:
        invoice_id = inv.get("id", "")
        inv_num = inv.get("invoice_number", 0)
        total = inv.get("total", 0)
        customer_email = inv.get("customer_email") or None
        customer_phone = inv.get("customer_phone") or None

        if not customer_email and not customer_phone:
            results["skipped"] += 1
            results["details"].append({"id": invoice_id, "status": "no_contact"})
            continue

        try:
            notif_result = await send_invoice_notification(
                email=customer_email or "",
                phone=customer_phone or "",
                invoice_number=inv_num,
                total=float(total),
                portal_link="",
                send_email_func=send_email_func,
                send_sms_func=send_sms_func,
            )
            results["sent"] += 1
            results["details"].append({
                "id": invoice_id,
                "status": "sent",
                "to": customer_email or customer_phone,
                "channels": notif_result,
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({"id": invoice_id, "status": "error", "error": str(e)})

    return results


def get_due_invoices(invoices: list[dict], now_ms: int) -> list[dict]:
    """Filter invoices that are overdue.

    Overdue = status in (sent, partial) AND due_date is in the past.
    """
    return [
        inv
        for inv in invoices
        if inv.get("status") in ("sent", "partial")
        and inv.get("due_date", 0) > 0
        and inv.get("due_date", 0) < now_ms
    ]


def get_invoice_link(app_url: str, invoice: dict) -> str:
    """Build the portal link for an invoice."""
    return f"{app_url}/portal/"
