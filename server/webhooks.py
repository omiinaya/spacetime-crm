"""Webhook delivery engine for SpacetimeCRM.
Dispatches events to all active, matching webhook subscriptions with HMAC-SHA256 signing.
"""
import asyncio
import hashlib
import hmac
import json
import logging
from typing import Any, Optional
from datetime import datetime, timezone

import httpx
from client import get_http_client

logger = logging.getLogger(__name__)

# ── Event type constants ────────────────────────────────────────

EVENT_CUSTOMER_CREATED = "customer.created"
EVENT_CUSTOMER_UPDATED = "customer.updated"
EVENT_CUSTOMER_DELETED = "customer.deleted"
EVENT_TICKET_CREATED = "ticket.created"
EVENT_TICKET_UPDATED = "ticket.updated"
EVENT_TICKET_STATUS_CHANGED = "ticket.status_changed"
EVENT_INVOICE_CREATED = "invoice.created"
EVENT_INVOICE_STATUS_CHANGED = "invoice.status_changed"
EVENT_INVOICE_PAID = "invoice.paid"
EVENT_PAYMENT_CREATED = "payment.created"
EVENT_ESTIMATE_CREATED = "estimate.created"
EVENT_ESTIMATE_APPROVED = "estimate.approved"
EVENT_APPOINTMENT_CREATED = "appointment.created"

ALL_EVENTS = [
    EVENT_CUSTOMER_CREATED,
    EVENT_CUSTOMER_UPDATED,
    EVENT_CUSTOMER_DELETED,
    EVENT_TICKET_CREATED,
    EVENT_TICKET_UPDATED,
    EVENT_TICKET_STATUS_CHANGED,
    EVENT_INVOICE_CREATED,
    EVENT_INVOICE_STATUS_CHANGED,
    EVENT_INVOICE_PAID,
    EVENT_PAYMENT_CREATED,
    EVENT_ESTIMATE_CREATED,
    EVENT_ESTIMATE_APPROVED,
    EVENT_APPOINTMENT_CREATED,
]


def _sign_payload(payload: bytes, secret: str) -> str:
    """HMAC-SHA256 sign a payload with the given secret."""
    if not secret:
        return ""
    h = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256)
    return h.hexdigest()


async def _deliver(
    url: str,
    event_type: str,
    payload: dict[str, Any],
    secret: str,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Deliver a single webhook event. Returns delivery result."""
    body_dict = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }
    body_bytes = json.dumps(body_dict).encode("utf-8")
    signature = _sign_payload(body_bytes, secret)

    last_error: Optional[str] = None
    status_code: Optional[int] = None

    for attempt in range(1, max_retries + 1):
        try:
            client = get_http_client()
            resp = await client.post(
                url,
                content=body_bytes,
                timeout=10.0,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                    "X-Webhook-Event": event_type,
                    "User-Agent": "SpacetimeCRM-Webhook/1.0",
                },
            )
            status_code = resp.status_code
            if status_code is not None and status_code < 500:
                # Success or client error — don't retry
                return {
                    "ok": 200 <= status_code < 300,
                    "status_code": status_code,
                    "attempt": attempt,
                    "error": None if 200 <= status_code < 300 else f"HTTP {status_code}",
                }
            last_error = f"HTTP {status_code}" if status_code else "No response"
        except httpx.TimeoutException:
            last_error = "timeout"
        except httpx.RequestError as e:
            last_error = str(e)

        if attempt < max_retries:
            # Exponential backoff: 1s, 2s, 4s
            await asyncio.sleep(1 * (2 ** (attempt - 1)))

    return {
        "ok": False,
        "status_code": status_code,
        "attempt": max_retries,
        "error": last_error,
    }


async def fire_event(
    event_type: str,
    payload: dict[str, Any],
    subscriptions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fire an event to all active, matching webhook subscriptions.

    Args:
        event_type: The event type string (e.g. "ticket.created")
        payload: Event payload dict
        subscriptions: List of subscription dicts from STDB, each must have
                      id, url, events (comma-sep), secret, active fields.

    Returns:
        List of delivery result dicts.
    """
    results: list[dict[str, Any]] = []

    for sub in subscriptions:
        if not sub.get("active", False):
            continue
        sub_events = sub.get("events", "")
        event_list = [e.strip() for e in sub_events.split(",") if e.strip()]
        if event_type not in event_list:
            continue

        result = await _deliver(
            url=sub["url"],
            event_type=event_type,
            payload=payload,
            secret=sub.get("secret", ""),
        )
        result["subscription_id"] = sub.get("id", "")
        result["url"] = sub["url"]
        results.append(result)

        if not result["ok"]:
            logger.warning(
                "Webhook delivery failed: %s -> %s (%s)",
                event_type, sub["url"], result.get("error"),
            )
        else:
            logger.info(
                "Webhook delivered: %s -> %s (HTTP %s)",
                event_type, sub["url"], result.get("status_code"),
            )

    return results
