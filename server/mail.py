"""Email notification utility for SpacetimeCRM.
Uses smtplib with configurable SMTP settings stored in a JSON file.
"""

import json
import logging
import smtplib
import ssl
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional
from helpers import jinja_env

logger = logging.getLogger(__name__)

SETTINGS_PATH = Path(__file__).resolve().parent / "mail_settings.json"


def _load_settings() -> dict | None:
    if not SETTINGS_PATH.exists():
        return None
    try:
        with open(SETTINGS_PATH) as f:
            return json.load(f)
    except Exception as e:
        logger.error("Failed to load mail settings: %s", e)
        return None


def _save_settings(settings: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))
    logger.info("Mail settings saved to %s", SETTINGS_PATH)


def get_settings() -> dict | None:
    settings = _load_settings()
    if not settings:
        return None
    # Never return the password
    return {
        "host": settings.get("host", ""),
        "port": settings.get("port", 587),
        "username": settings.get("username", ""),
        "use_tls": settings.get("use_tls", True),
        "sender_name": settings.get("sender_name", "SpacetimeCRM"),
        "sender_email": settings.get("sender_email", ""),
    }


def update_settings(data: dict) -> dict:
    current = _load_settings() or {}
    current.update(
        {
            "host": data.get("host", current.get("host", "")),
            "port": data.get("port", current.get("port", 587)),
            "username": data.get("username", current.get("username", "")),
            "use_tls": data.get("use_tls", current.get("use_tls", True)),
            "sender_name": data.get("sender_name", current.get("sender_name", "SpacetimeCRM")),
            "sender_email": data.get("sender_email", current.get("sender_email", "")),
        }
    )
    if "password" in data:
        current["password"] = data["password"]
    _save_settings(current)
    return get_settings()


def send_email(to: str, subject: str, html_body: str, text_body: str | None = None) -> bool:
    """Send an email via configured SMTP. Returns True on success."""
    settings = _load_settings()
    if not settings:
        logger.warning("Mail not configured — skipping email to %s", to)
        return False

    host = settings.get("host", "")
    port = settings.get("port", 587)
    username = settings.get("username", "")
    password = settings.get("password", "")
    sender_name = settings.get("sender_name", "SpacetimeCRM")
    sender_email = settings.get("sender_email", "")

    if not host or not sender_email:
        logger.warning("Mail settings incomplete — skipping email to %s", to)
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = to
    msg["Subject"] = subject

    # Plain text fallback
    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    else:
        msg.attach(MIMEText("Please view this email in an HTML client.", "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        context = ssl.create_default_context()
        use_tls = settings.get("use_tls", True)

        if use_tls:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                if username:
                    server.login(username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP_SSL(host, port, timeout=15, context=context) as server:
                if username:
                    server.login(username, password)
                server.send_message(msg)

        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False


def test_connection() -> dict:
    """Test the current SMTP configuration. Returns result dict."""
    settings = _load_settings()
    if not settings:
        return {"ok": False, "error": "Mail not configured"}

    host = settings.get("host", "")
    port = settings.get("port", 587)
    username = settings.get("username", "")
    password = settings.get("password", "")
    sender_email = settings.get("sender_email", "")

    if not host or not sender_email:
        return {"ok": False, "error": "Host and sender email required"}

    try:
        context = ssl.create_default_context()
        use_tls = settings.get("use_tls", True)

        if use_tls:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.ehlo()
                status = server.ehlo_resp  # pylint: disable=maybe-no-member
                server.starttls(context=context)
                server.ehlo()
                if username:
                    server.login(username, password)
        else:
            with smtplib.SMTP_SSL(host, port, timeout=10, context=context) as server:
                if username:
                    server.login(username, password)

        return {"ok": True, "message": f"Connected to {host}:{port}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Notification templates ──

_STATUS_LABELS = {
    "new": "New",
    "in_progress": "In Progress",
    "waiting_parts": "Waiting for Parts",
    "waiting_customer": "Waiting for Customer",
    "resolved": "Resolved",
    "closed": "Closed",
}


def _customer_email(customer: dict | None) -> str | None:
    """Get customer's preferred notification email address."""
    if not customer:
        return None
    return customer.get("email") or None


def _notify_ticket_status_change(customer_email: str, ticket_number: int, title: str, status: str, link: str) -> None:
    """Send ticket status notification."""
    status_label = _STATUS_LABELS.get(status, status)
    html = jinja_env.get_template("email/ticket_status.html").render(
        ticket_number=ticket_number,
        title=title,
        status_label=status_label,
        link=link,
    )
    send_email(customer_email, f"Ticket #{ticket_number} — {status_label}", html)


def _notify_invoice_created(customer_email: str, invoice_number: int, total: float, link: str) -> None:
    """Send invoice notification."""
    html = jinja_env.get_template("email/invoice_created.html").render(
        invoice_number=invoice_number,
        total=f"{total:.2f}",
        link=link,
    )
    send_email(customer_email, f"Invoice #{invoice_number} — ${total:.2f}", html)


def _notify_appointment_created(customer_email: str, title: str, start_time: int, link: str) -> None:
    """Send appointment notification."""
    dt = datetime.fromtimestamp(start_time / 1000)
    date_str = dt.strftime("%A, %B %d at %I:%M %p")
    html = jinja_env.get_template("email/appointment_created.html").render(
        title=title,
        date_str=date_str,
        link=link,
    )
    send_email(customer_email, f"Appointment: {title}", html)


def _notify_payment_received(customer_email: str, invoice_number: int, amount: float, link: str) -> None:
    """Send payment confirmation."""
    html = jinja_env.get_template("email/payment_received.html").render(
        amount=f"{amount:.2f}",
        invoice_number=invoice_number,
        link=link,
    )
    send_email(customer_email, f"Payment Received — Invoice #{invoice_number}", html)


def _notify_estimate_approved(customer_email: str, estimate_number: int, total: float, link: str) -> None:
    """Send estimate approved notification."""
    html = jinja_env.get_template("email/estimate_approved.html").render(
        estimate_number=estimate_number,
        total=f"{total:.2f}",
        link=link,
    )
    send_email(customer_email, f"Estimate #{estimate_number} Approved", html)


def _notify_low_stock(admin_email: str, products: list[dict]) -> None:
    """Send low stock alert to admin."""
    if not products:
        return
    items = [
        {
            "name": p.get("name", "?"),
            "sku": p.get("sku", "-"),
            "qty": f"{p.get('quantity_on_hand', 0):.0f}",
            "min": f"{p.get('min_stock', 0):.0f}",
        }
        for p in products
    ]
    html = jinja_env.get_template("email/low_stock.html").render(
        products=items,
        count=len(products),
    )
    send_email(admin_email, f"⚠️ Low Stock Alert — {len(products)} product(s) below threshold", html)


def _notify_appointment_reminder(customer_email: str, title: str, start_time: int, link: str) -> None:
    """Send appointment reminder email (24h before)."""
    dt = datetime.fromtimestamp(start_time / 1000)
    date_str = dt.strftime("%A, %B %d at %I:%M %p")
    html = jinja_env.get_template("email/appointment_reminder.html").render(
        title=title,
        date_str=date_str,
        link=link,
    )
    send_email(customer_email, f"Reminder: {title} — Tomorrow", html)


def _notify_overdue_reminder(customer_email: str, invoice_number: int, total: float, due_date: str, link: str) -> None:
    """Send overdue invoice reminder email."""
    html = jinja_env.get_template("email/overdue_reminder.html").render(
        invoice_number=invoice_number,
        total=f"{total:.2f}",
        customer_name="Valued Customer",
        due_date=due_date,
        link=link,
    )
    send_email(customer_email, f"Overdue Invoice #{invoice_number} — ${total:.2f}", html)
