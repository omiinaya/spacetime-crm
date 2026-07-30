"""Webhook routes — Stripe + webhook subscriptions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from helpers import (
    _call,
    _get_webhook_subscriptions,
    _log_audit,
    _sql,
    logger,
    require_role,
)
from models import WebhookSubscriptionCreate, WebhookSubscriptionUpdate
from stripe_payments import verify_webhook
from webhooks import ALL_EVENTS as WEBHOOK_EVENTS
from webhooks import _deliver

router = APIRouter()


@router.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events (checkout.session.completed)."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    event = await verify_webhook(payload, sig_header)
    if not event:
        raise HTTPException(400, "Invalid webhook signature")

    event_type = event.get("type", "")
    logger.info("Stripe webhook received: %s", event_type)

    if event_type == "checkout.session.completed":
        session = event.get("data", {}).get("object", {})
        metadata = session.get("metadata", {})
        invoice_id = metadata.get("invoice_id", "")
        customer_id = metadata.get("customer_id", "")
        amount_total = float(session.get("amount_total", 0)) / 100.0
        payment_intent = session.get("payment_intent", "")
        stripe_session_id = session.get("id", "")

        if invoice_id and amount_total > 0:
            inv_rows = await _sql(
                f"SELECT tenant_id FROM invoices WHERE id = '{invoice_id}'"
            )
            tid = inv_rows[0]["tenant_id"] if inv_rows else ""
            await _call(
                "record_payment",
                [
                    tid,
                    invoice_id,
                    customer_id,
                    amount_total,
                    "stripe",
                    payment_intent,
                    f"Stripe payment via session {stripe_session_id}",
                    "USD",
                ],
            )

            # Update invoice status
            payments = await _sql(
                f"SELECT * FROM payment WHERE invoice_id = '{invoice_id}'"
            )
            invs = await _sql(f"SELECT * FROM invoices WHERE id = '{invoice_id}'")
            if invs:
                inv = invs[0]
                total_paid = sum(float(p.get("amount", 0)) for p in payments)
                inv_total = float(inv.get("total", 0))
                new_status = "paid" if total_paid >= inv_total else "partial"
                if new_status != inv.get("status"):
                    await _call("update_invoice_status", [invoice_id, new_status])

    return {"ok": True}


# ── WEBHOOK SUBSCRIPTIONS ──


@router.get("/api/webhook-subscriptions")
async def list_webhook_subscriptions(
    offset: int = 0, limit: int = 50, user: dict = Depends(require_role("admin"))
):
    """List all webhook subscriptions with pagination."""
    rows = await _get_webhook_subscriptions()
    total = len(rows)
    rows = rows[offset : offset + limit]
    return {"subscriptions": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/api/webhook-subscriptions")
async def create_webhook_subscription(
    body: WebhookSubscriptionCreate, user: dict = Depends(require_role("admin"))
):
    """Create a new webhook subscription."""
    url = body.url.strip()
    events = body.events.strip()
    secret = body.secret.strip()

    if not url:
        raise HTTPException(400, "url is required")
    if not events:
        raise HTTPException(400, "events is required")

    valid_events = set(WEBHOOK_EVENTS)
    given_events = {e.strip() for e in events.split(",") if e.strip()}
    invalid = given_events - valid_events
    if invalid:
        raise HTTPException(400, f"Invalid event(s): {', '.join(invalid)}")

    await _call("create_webhook_subscription", [user["tenant_id"], url, events, secret])
    await _log_audit(user, "create", "webhook_subscription", url, events)
    return {"ok": True}


@router.put("/api/webhook-subscriptions/{sub_id}")
async def update_webhook_subscription(
    sub_id: str,
    body: WebhookSubscriptionUpdate,
    user: dict = Depends(require_role("admin")),
):
    """Update a webhook subscription."""
    url = body.url.strip()
    events = body.events.strip()
    secret = body.secret.strip()
    active = body.active

    if not url:
        raise HTTPException(400, "url is required")

    if events:
        valid_events = set(WEBHOOK_EVENTS)
        given_events = {e.strip() for e in events.split(",") if e.strip()}
        invalid = given_events - valid_events
        if invalid:
            raise HTTPException(400, f"Invalid event(s): {', '.join(invalid)}")

    await _call("update_webhook_subscription", [sub_id, url, events, secret, active])
    await _log_audit(user, "update", "webhook_subscription", url, events)
    return {"ok": True}


@router.delete("/api/webhook-subscriptions/{sub_id}")
async def delete_webhook_subscription(
    sub_id: str, user: dict = Depends(require_role("admin"))
):
    """Delete a webhook subscription."""
    await _call("delete_webhook_subscription", [sub_id])
    await _log_audit(user, "delete", "webhook_subscription", sub_id)
    return {"ok": True}


@router.post("/api/webhook-subscriptions/{sub_id}/test")
async def test_webhook_subscription(
    sub_id: str, user: dict = Depends(require_role("admin"))
):
    """Send a test event to a specific subscription."""
    rows = await _sql(f"SELECT * FROM webhook_subscriptions WHERE id = '{sub_id}'")
    if not rows:
        raise HTTPException(404, "Subscription not found")
    sub = rows[0]
    test_payload = {
        "entity_type": "test",
        "id": "test_001",
        "message": "This is a test webhook event from SpacetimeCRM.",
    }
    result = await _deliver(
        url=sub["url"],
        event_type="test.ping",
        payload=test_payload,
        secret=sub.get("secret", ""),
        max_retries=1,
    )
    return result
