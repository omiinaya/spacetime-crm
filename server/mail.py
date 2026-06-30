"""Email notification utility for SpacetimeCRM.
Uses smtplib with configurable SMTP settings stored in a JSON file.
"""
import json
import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SETTINGS_PATH = Path(__file__).resolve().parent / "mail_settings.json"


def _load_settings() -> Optional[dict]:
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


def get_settings() -> Optional[dict]:
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
    current.update({
        "host": data.get("host", current.get("host", "")),
        "port": data.get("port", current.get("port", 587)),
        "username": data.get("username", current.get("username", "")),
        "use_tls": data.get("use_tls", current.get("use_tls", True)),
        "sender_name": data.get("sender_name", current.get("sender_name", "SpacetimeCRM")),
        "sender_email": data.get("sender_email", current.get("sender_email", "")),
    })
    if "password" in data:
        current["password"] = data["password"]
    _save_settings(current)
    return get_settings()


def send_email(to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
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

def _customer_email(customer: Optional[dict]) -> Optional[str]:
    """Get customer's preferred notification email address."""
    if not customer:
        return None
    return customer.get("email") or None


def _notify_ticket_status_change(customer_email: str, ticket_number: int, title: str, status: str, link: str) -> None:
    """Send ticket status notification."""
    status_labels = {
        "new": "New", "in_progress": "In Progress",
        "waiting_parts": "Waiting for Parts", "waiting_customer": "Waiting for Customer",
        "resolved": "Resolved", "closed": "Closed",
    }
    status_label = status_labels.get(status, status)
    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#333">Ticket #{ticket_number} — {status_label}</h2>
<p>Your ticket <strong>"{title}"</strong> has been updated to <strong>{status_label}</strong>.</p>
<p><a href="{link}" style="display:inline-block;background:#6366f1;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none">View in Portal</a></p>
<hr style="border:none;border-top:1px solid #eee" />
<p style="color:#999;font-size:12px">SpacetimeCRM Customer Portal</p>
</body></html>"""
    send_email(customer_email, f"Ticket #{ticket_number} — {status_label}", html)


def _notify_invoice_created(customer_email: str, invoice_number: int, total: float, link: str) -> None:
    """Send invoice notification."""
    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#333">Invoice #{invoice_number}</h2>
<p>A new invoice has been created for <strong>${total:.2f}</strong>.</p>
<p><a href="{link}" style="display:inline-block;background:#6366f1;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none">View & Pay Invoice</a></p>
<hr style="border:none;border-top:1px solid #eee" />
<p style="color:#999;font-size:12px">SpacetimeCRM Customer Portal</p>
</body></html>"""
    send_email(customer_email, f"Invoice #{invoice_number} — ${total:.2f}", html)


def _notify_appointment_created(customer_email: str, title: str, start_time: int, link: str) -> None:
    """Send appointment notification."""
    from datetime import datetime
    dt = datetime.fromtimestamp(start_time / 1000)
    date_str = dt.strftime("%A, %B %d at %I:%M %p")
    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#333">Appointment Scheduled</h2>
<p><strong>{title}</strong></p>
<p>When: <strong>{date_str}</strong></p>
<p><a href="{link}" style="display:inline-block;background:#6366f1;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none">View in Portal</a></p>
<hr style="border:none;border-top:1px solid #eee" />
<p style="color:#999;font-size:12px">SpacetimeCRM Customer Portal</p>
</body></html>"""
    send_email(customer_email, f"Appointment: {title}", html)


def _notify_payment_received(customer_email: str, invoice_number: int, amount: float, link: str) -> None:
    """Send payment confirmation."""
    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#333">Payment Received</h2>
<p>A payment of <strong>${amount:.2f}</strong> has been applied to Invoice #{invoice_number}.</p>
<p><a href="{link}" style="display:inline-block;background:#6366f1;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none">View Invoice</a></p>
<hr style="border:none;border-top:1px solid #eee" />
<p style="color:#999;font-size:12px">SpacetimeCRM Customer Portal</p>
</body></html>"""
    send_email(customer_email, f"Payment Received — Invoice #{invoice_number}", html)


def _notify_estimate_approved(customer_email: str, estimate_number: int, total: float, link: str) -> None:
    """Send estimate approved notification."""
    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#333">Estimate #{estimate_number} Approved</h2>
<p>Your estimate for <strong>${total:.2f}</strong> has been approved and an invoice is being created.</p>
<p><a href="{link}" style="display:inline-block;background:#6366f1;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none">View in Portal</a></p>
<hr style="border:none;border-top:1px solid #eee" />
<p style="color:#999;font-size:12px">SpacetimeCRM Customer Portal</p>
</body></html>"""
    send_email(customer_email, f"Estimate #{estimate_number} Approved", html)


def _notify_low_stock(admin_email: str, products: list[dict]) -> None:
    """Send low stock alert to admin."""
    if not products:
        return
    rows_html = "".join(
        f'<tr><td style="padding:8px;border-bottom:1px solid #eee">{p.get("name","?")}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:center">{p.get("sku","-")}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:center;color:#ef4444;font-weight:bold">{p.get("quantity_on_hand",0):.0f}</td>'
        f'<td style="padding:8px;border-bottom:1px solid #eee;text-align:center">{p.get("min_stock",0):.0f}</td>'
        f'</tr>'
        for p in products
    )
    html = f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
<h2 style="color:#333">⚠️ Low Stock Alert</h2>
<p>The following products are below their minimum stock threshold:</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0">
<thead><tr style="background:#f9fafb">
<th style="padding:8px;text-align:left;border-bottom:2px solid #e5e7eb">Product</th>
<th style="padding:8px;text-align:center;border-bottom:2px solid #e5e7eb">SKU</th>
<th style="padding:8px;text-align:center;border-bottom:2px solid #e5e7eb">On Hand</th>
<th style="padding:8px;text-align:center;border-bottom:2px solid #e5e7eb">Min Stock</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>
<p style="color:#999;font-size:12px">SpacetimeCRM — Inventory Alert</p>
</body></html>"""
    send_email(admin_email, f"⚠️ Low Stock Alert — {len(products)} product(s) below threshold", html)
