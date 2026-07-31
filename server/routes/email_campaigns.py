"""Email campaign routes — send bulk emails to customers."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from helpers import _sql, require_role
from mail import send_email

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/email-campaigns/send-blast")
async def send_email_blast(
    body: dict,
    user: dict = Depends(require_role("admin")),
):
    """Send a bulk email to customers matching the given filters.

    Body:
      subject (str): email subject
      html_body (str): HTML content
      customer_filter (str, optional): 'all' (default), 'with_email', 'recent'
      days_since_last (int, optional): for 'recent' filter, max days since last ticket
      send_test_only (str, optional): email address to send a single test email
    """
    subject = body.get("subject", "").strip()
    html_body = body.get("html_body", "").strip()
    customer_filter = body.get("customer_filter", "all")
    send_test_only = body.get("send_test_only", "").strip()

    if not subject:
        raise HTTPException(400, "Subject is required")
    if not html_body:
        raise HTTPException(400, "Email body is required")

    # ── Test mode: send to one address ──
    if send_test_only:
        ok = send_email(send_test_only, subject, html_body)
        if not ok:
            raise HTTPException(500, "Failed to send test email — check mail settings")
        return {"ok": True, "sent": 1, "mode": "test", "recipients": [send_test_only]}

    # ── Build recipient list ──
    where_clauses = ["tenant_id = '" + user["tenant_id"] + "'"]

    if customer_filter == "with_email":
        where_clauses.append("email IS NOT NULL AND email != ''")
    elif customer_filter == "recent":
        # Customers with tickets in the last N days
        days = max(int(body.get("days_since_last", 30)), 1)
        cutoff = int(time.time() * 1000) - (days * 86400 * 1000)
        where_clauses.append(
            "id IN (SELECT DISTINCT customer_id FROM ticket WHERE created_at >= "
            + str(cutoff)
            + ")"
        )
        where_clauses.append("email IS NOT NULL AND email != ''")
    else:
        # 'all' — include anonymous customers with an email
        where_clauses.append("email IS NOT NULL AND email != ''")

    where_sql = " AND ".join(where_clauses)

    try:
        rows = await _sql(
            f"SELECT id, first_name, last_name, email FROM customer WHERE {where_sql} ORDER BY created_at DESC LIMIT 500"
        )
    except Exception as e:
        logger.error("Failed to query customers for blast: %s", e)
        raise HTTPException(500, "Failed to query customers") from e

    if not rows:
        raise HTTPException(400, "No customers match the given filter")

    # ── Send emails ──
    recipients = []
    failed = 0
    for row in rows:
        email = row.get("email", "").strip()
        if not email:
            continue
        # Personalize the HTML body with customer name
        name = (
            f"{row.get('first_name', '')} {row.get('last_name', '')}".strip() or "Valued Customer"
        )
        personalized_body = html_body.replace("{{name}}", name).replace("{{email}}", email)
        ok = send_email(email, subject, personalized_body)
        if ok:
            recipients.append(email)
        else:
            failed += 1

    logger.info(
        "Email blast sent: %d succeeded, %d failed, filter=%s",
        len(recipients),
        failed,
        customer_filter,
    )

    return {
        "ok": True,
        "sent": len(recipients),
        "failed": failed,
        "total_matched": len(rows),
        "recipients": recipients[:10],  # Show first 10 in response
    }
