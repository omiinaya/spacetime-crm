"""SMS notification utility for SpacetimeCRM.
Uses Twilio REST API with configurable settings stored in a JSON file.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from client import get_http_client

# FIXME: BLE001 - Blind except
# FIXME: DTZ006 - datetime.fromtimestamp without tz
# FIXME: TRY401 - Redundant exception in logging

logger = logging.getLogger(__name__)

SETTINGS_PATH = Path(__file__).resolve().parent / "sms_settings.json"


def _load_settings() -> dict | None:
    if not SETTINGS_PATH.exists():
        return None
    try:
        with open(SETTINGS_PATH) as f:
            return json.load(f)
    except Exception as e:
        logger.exception("Failed to load SMS settings")
        return None


def _save_settings(settings: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))
    logger.info("SMS settings saved to %s", SETTINGS_PATH)


def get_settings() -> dict | None:
    settings = _load_settings()
    if not settings:
        return None
    return {
        "account_sid": settings.get("account_sid", ""),
        "from_number": settings.get("from_number", ""),
        "configured": bool(settings.get("account_sid") and settings.get("auth_token") and settings.get("from_number")),
    }


def update_settings(data: dict) -> dict:
    current = _load_settings() or {}
    current.update(
        {
            "account_sid": data.get("account_sid", current.get("account_sid", "")),
            "from_number": data.get("from_number", current.get("from_number", "")),
        },
    )
    if data.get("auth_token"):
        current["auth_token"] = data["auth_token"]
    _save_settings(current)
    return get_settings()


def is_configured() -> bool:
    settings = _load_settings()
    if not settings:
        return False
    return bool(settings.get("account_sid") and settings.get("auth_token") and settings.get("from_number"))


def _customer_phone(customer: dict | None) -> str | None:
    """Get customer's preferred notification phone number."""
    if not customer:
        return None
    return customer.get("mobile") or customer.get("phone") or None


async def send_sms(to: str, body: str) -> bool:
    """Send an SMS via Twilio REST API. Returns True on success."""
    settings = _load_settings()
    if not settings:
        logger.warning("SMS not configured — skipping SMS to %s", to)
        return False

    account_sid = settings.get("account_sid", "")
    auth_token = settings.get("auth_token", "")
    from_number = settings.get("from_number", "")

    if not account_sid or not auth_token or not from_number:
        logger.warning("SMS settings incomplete — skipping SMS to %s", to)
        return False

    # Normalize phone number: strip non-digits, ensure + prefix
    to = to.strip()
    if not to.startswith("+"):
        # Assume US number if 10 digits
        digits = "".join(c for c in to if c.isdigit())
        if len(digits) == 10:
            to = f"+1{digits}"
        elif len(digits) == 11 and digits.startswith("1"):
            to = f"+{digits}"
        else:
            to = f"+{digits}"

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

    try:
        client = get_http_client()
        resp = await client.post(
            url,
            auth=(account_sid, auth_token),
            data={"From": from_number, "To": to, "Body": body},
            timeout=15,
        )
        if resp.status_code < 400:
            logger.info("SMS sent to %s: %.60s", to, body)
            return True
        error_data = resp.json()
        logger.error(
            "Twilio API error: %s — %s",
            resp.status_code,
            error_data.get("message", resp.text[:200]),
        )
        return False
    except Exception as e:
        logger.exception("Failed to send SMS to %s: %s", to, e)
        return False


async def test_connection() -> dict:
    """Test Twilio config by fetching account info. Returns result dict."""
    settings = _load_settings()
    if not settings:
        return {"ok": False, "error": "SMS not configured"}

    account_sid = settings.get("account_sid", "")
    auth_token = settings.get("auth_token", "")
    from_number = settings.get("from_number", "")

    if not account_sid or not auth_token:
        return {"ok": False, "error": "Account SID and Auth Token required"}

    try:
        client = get_http_client()
        resp = await client.get(
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json",
            auth=(account_sid, auth_token),
            timeout=10,
        )
        if resp.status_code < 400:
            data = resp.json()
            friendly_name = data.get("friendly_name", "Twilio Account")
            return {
                "ok": True,
                "message": f"Connected: {friendly_name}",
                "from_number": from_number,
            }
        return {"ok": False, "error": f"Twilio API error: {resp.status_code}"}
    except Exception as e:
    logger.exception("Connection test failed")

        return {"ok": False, "error": str(e)}
        return {"ok": False, "error": str(e)}


# ── Notification templates ──


def _notify_ticket_status_change(phone: str, ticket_number: int, title: str, status: str) -> None:
    """Send ticket status SMS notification. Fire-and-forget."""
    status_labels = {
        "new": "New",
        "in_progress": "In Progress",
        "waiting_parts": "Waiting for Parts",
        "waiting_customer": "Waiting for Customer",
        "resolved": "Resolved",
        "closed": "Closed",
    }
    status_label = status_labels.get(status, status)
    body = f'Ticket #{ticket_number} — {status_label}: "{title[:40]}"'
    asyncio.ensure_future(send_sms(phone, body))


def _notify_invoice_created(phone: str, invoice_number: int, total: float) -> None:
    """Send invoice created SMS notification."""
    body = f"Invoice #{invoice_number} for ${total:.2f} is ready. View & pay in your customer portal."
    asyncio.ensure_future(send_sms(phone, body))


def _notify_payment_received(phone: str, invoice_number: int, amount: float) -> None:
    """Send payment confirmation SMS."""
    body = f"Payment of ${amount:.2f} received for Invoice #{invoice_number}. Thank you!"
    asyncio.ensure_future(send_sms(phone, body))


def _notify_appointment_created(phone: str, title: str, start_time: int) -> None:
    """Send appointment reminder SMS."""
    dt = datetime.fromtimestamp(start_time / 1000, tz=UTC)
    date_str = dt.strftime("%A, %B %d at %I:%M %p")
    body = f"Appointment scheduled: {title} on {date_str}"
    asyncio.ensure_future(send_sms(phone, body))


def _notify_appointment_reminder(phone: str, title: str, start_time: int) -> None:
    """Send appointment reminder SMS (24h before)."""
    dt = datetime.fromtimestamp(start_time / 1000, tz=UTC)
    date_str = dt.strftime("%A, %B %d at %I:%M %p")
    body = f"Reminder: {title} tomorrow at {date_str}. See you then!"
    asyncio.ensure_future(send_sms(phone, body))


def _notify_estimate_approved(phone: str, estimate_number: int, total: float) -> None:
    """Send estimate approved SMS notification."""
    body = f"Estimate #{estimate_number} for ${total:.2f} approved. An invoice is being created."
    asyncio.ensure_future(send_sms(phone, body))


def _notify_overdue_reminder(phone: str, invoice_number: int, total: float) -> None:
    """Send overdue invoice reminder SMS."""
    body = f"Reminder: Invoice #{invoice_number} for ${total:.2f} is overdue. Please arrange payment. Reply or call us to discuss."
    asyncio.ensure_future(send_sms(phone, body))
