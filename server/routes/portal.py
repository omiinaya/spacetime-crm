"""Customer portal routes + Stripe checkout session creation."""
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from config import settings
from helpers import _safe_id, (
    _sql, _call, _sort, _log_audit, _fire_webhook,
    _safe_customer, logger, security,
)
from rate_limit import limiter
from models import (
    PortalLoginRequest, PortalNoteCreate, PortalPaymentCreate,
    PortalSetPassword, PortalCheckoutSessionCreate, PortalPayWithSavedCard,
)
from stripe_payments import create_checkout_session, create_payment_intent, is_configured as stripe_configured

router = APIRouter()


# ── Auth dependency ────────────────────────────────────────────


async def get_current_customer(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """FastAPI dependency that validates customer JWT and returns customer dict."""
    if credentials is None:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

    if payload.get("type") != "portal":
        raise HTTPException(401, "Not a customer token")

    customer_id = payload.get("sub")
    if not customer_id:
        raise HTTPException(401, "Invalid token: no subject")

    rows = await _sql(f"SELECT * FROM customer WHERE id = '{_safe_id(customer_id)}'")
    if not rows:
        raise HTTPException(401, "Customer not found")
    return _safe_customer(rows[0])


# ── Auth ───────────────────────────────────────────────────────


@router.post("/api/portal/login")
@limiter.limit("10/minute")
async def portal_login(request: Request, body: PortalLoginRequest):
    """Customer portal login with email + portal password."""
    email = body.email
    password = body.password

    if not email or not password:
        raise HTTPException(400, "Email and password required")

    rows = await _sql(f"SELECT * FROM customer WHERE email = '{_sanitize_sql(email)}'")
    if not rows:
        raise HTTPException(401, "Invalid email or password")

    customer = rows[0]
    pw_hash = customer.get("portal_password_hash", "")

    if not pw_hash or not bcrypt.checkpw(password.encode(), pw_hash.encode()):
        raise HTTPException(401, "Invalid email or password")

    now = datetime.now(timezone.utc)
    payload = {
        "sub": customer["id"],
        "tenant_id": customer.get("tenant_id", ""),
        "exp": now + timedelta(hours=settings.jwt_expire_hours),
        "iat": now,
        "type": "portal",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {
        "token": token,
        "customer": {
            "id": customer["id"],
            "first_name": customer.get("first_name", ""),
            "last_name": customer.get("last_name", ""),
            "email": customer.get("email", ""),
            "tenant_id": customer.get("tenant_id", ""),
        },
    }


# ── Profile ────────────────────────────────────────────────────


@router.get("/api/portal/me")
async def portal_me(customer: dict = Depends(get_current_customer)):
    """Return current customer info (safe fields only)."""
    return {
        "id": customer["id"],
        "first_name": customer.get("first_name", ""),
        "last_name": customer.get("last_name", ""),
        "email": customer["email"],
        "company": customer.get("company", ""),
        "phone": customer.get("phone", ""),
        "mobile": customer.get("mobile", ""),
        "address_line1": customer.get("address_line1", ""),
        "address_line2": customer.get("address_line2", ""),
        "city": customer.get("city", ""),
        "state": customer.get("state", ""),
        "zip": customer.get("zip", ""),
    }


@router.get("/api/portal/stats")
async def portal_stats(customer: dict = Depends(get_current_customer)):
    """Dashboard stats for the customer."""
    cid = customer["id"]
    tickets = await _sql(f"SELECT * FROM ticket WHERE customer_id = '{_safe_id(cid)}'")
    invoices = await _sql(f"SELECT * FROM invoices WHERE customer_id = '{_safe_id(cid)}'")
    appointments = await _sql(f"SELECT * FROM appointment WHERE customer_id = '{_safe_id(cid)}'")
    open_tickets = sum(1 for t in tickets if t.get("status") not in ("resolved", "closed"))
    total_billed = sum(float(i.get("total", 0)) for i in invoices if i.get("status") not in ("cancelled", "draft"))
    total_paid = sum(float(i.get("total", 0)) for i in invoices if i.get("status") == "paid")
    upcoming = [a for a in appointments if a.get("start_time", 0) > 0]
    return {
        "total_tickets": len(tickets),
        "open_tickets": open_tickets,
        "total_invoices": len(invoices),
        "total_billed": total_billed,
        "total_paid": total_paid,
        "balance_due": total_billed - total_paid,
        "upcoming_appointments": len(upcoming),
    }


# ── Tickets ────────────────────────────────────────────────────


@router.get("/api/portal/tickets")
async def portal_tickets(customer: dict = Depends(get_current_customer)):
    """Customer's tickets."""
    rows = await _sql(f"SELECT * FROM ticket WHERE customer_id = '{customer['id']}'")
    users = await _sql("SELECT * FROM user")
    user_map = {u["id"]: u["name"] for u in users}
    for t in rows:
        t["assigned_name"] = user_map.get(t.get("assigned_user_id", ""), "")
    return {"tickets": _sort(rows, "created_at")}


@router.get("/api/portal/tickets/{ticket_id}")
async def portal_ticket_detail(ticket_id: str, customer: dict = Depends(get_current_customer)):
    """Single ticket detail with notes (customer-owned only)."""
    rows = await _sql(f"SELECT * FROM ticket WHERE id = '{_safe_id(ticket_id)}' AND customer_id = '{customer['id']}'")
    if not rows:
        raise HTTPException(404, "Ticket not found")
    ticket = rows[0]
    notes = await _sql(f"SELECT * FROM ticket_note WHERE ticket_id = '{_safe_id(ticket_id)}' AND internal = false")
    ticket["notes"] = _sort(notes, "created_at", desc=False)
    users = await _sql("SELECT * FROM user")
    user_map = {u["id"]: u["name"] for u in users}
    ticket["assigned_name"] = user_map.get(ticket.get("assigned_user_id", ""), "")
    return {"ticket": ticket}


@router.post("/api/portal/tickets/{ticket_id}/notes")
async def portal_add_note(ticket_id: str, body: PortalNoteCreate, customer: dict = Depends(get_current_customer)):
    """Customer adds a note to their ticket."""
    rows = await _sql(f"SELECT * FROM ticket WHERE id = '{_safe_id(ticket_id)}' AND customer_id = '{customer['id']}'")
    if not rows:
        raise HTTPException(404, "Ticket not found")
    await _call("add_ticket_note", [
        ticket_id,
        f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or "Customer",
        body.content,
        False,
    ])
    return {"ok": True}


# ── Invoices ───────────────────────────────────────────────────


@router.get("/api/portal/invoices")
async def portal_invoices(customer: dict = Depends(get_current_customer)):
    """Customer's invoices."""
    rows = await _sql(f"SELECT * FROM invoices WHERE customer_id = '{customer['id']}'")
    return {"invoices": _sort(rows, "created_at")}


@router.get("/api/portal/invoices/{invoice_id}")
async def portal_invoice_detail(invoice_id: str, customer: dict = Depends(get_current_customer)):
    """Single invoice detail with line items (customer-owned only)."""
    rows = await _sql(f"SELECT * FROM invoices WHERE id = '{_safe_id(invoice_id)}' AND customer_id = '{customer['id']}'")
    if not rows:
        raise HTTPException(404, "Invoice not found")
    inv = rows[0]
    items = await _sql(f"SELECT * FROM invoice_line_items WHERE invoice_id = '{_safe_id(invoice_id)}'")
    inv["line_items"] = _sort(items, "sort_order", desc=False)
    payments = await _sql(f"SELECT * FROM payment WHERE invoice_id = '{_safe_id(invoice_id)}'")
    inv["payments"] = _sort(payments, "created_at")
    total_paid = sum(float(p.get("amount", 0)) for p in payments)
    inv["total_paid"] = total_paid
    inv["balance_due"] = float(inv.get("total", 0)) - total_paid
    return {"invoice": inv}


# ── Payments ───────────────────────────────────────────────────


@router.post("/api/portal/payments")
async def portal_make_payment(body: PortalPaymentCreate, customer: dict = Depends(get_current_customer)):
    """Customer makes a payment on an invoice."""
    invoice_id = body.invoice_id
    amount = body.amount
    method = body.method

    rows = await _sql(f"SELECT * FROM invoices WHERE id = '{_safe_id(invoice_id)}' AND customer_id = '{customer['id']}'")
    if not rows:
        raise HTTPException(404, "Invoice not found")

    await _call("record_payment", [
        customer.get("tenant_id", ""),
        invoice_id,
        customer["id"],
        amount,
        method,
        body.reference,
        "Online payment via customer portal",
        "USD",
    ])

    payments = await _sql(f"SELECT * FROM payment WHERE invoice_id = '{_safe_id(invoice_id)}'")
    inv = rows[0]
    total_paid = sum(float(p.get("amount", 0)) for p in payments)
    inv_total = float(inv.get("total", 0))
    new_status = "paid" if total_paid >= inv_total else "partial" if total_paid > 0 else inv.get("status", "draft")
    if new_status != inv.get("status"):
        await _call("update_invoice_status", [invoice_id, new_status])

    return {"ok": True}


# ── Appointments ───────────────────────────────────────────────


@router.get("/api/portal/appointments")
async def portal_appointments(customer: dict = Depends(get_current_customer)):
    """Customer's appointments."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    rows = await _sql(f"SELECT * FROM appointment WHERE customer_id = '{customer['id']}'")
    upcoming = [a for a in rows if a.get("start_time", 0) > now_ms]
    past = [a for a in rows if a.get("start_time", 0) <= now_ms]
    return {
        "appointments": _sort(rows, "start_time", desc=False),
        "upcoming": _sort(upcoming, "start_time", desc=False),
        "past": _sort(past, "start_time", desc=False),
    }


# ── Settings ───────────────────────────────────────────────────


@router.post("/api/portal/customer/set-password")
async def portal_set_password(body: PortalSetPassword, customer: dict = Depends(get_current_customer)):
    """Customer sets/changes their portal password."""
    pw = body.password
    if len(pw) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    await _call("set_customer_password", [customer["id"], hashed])
    return {"ok": True}


# ── Stripe Checkout ────────────────────────────────────────────


@router.post("/api/portal/payments/create-checkout-session")
async def portal_create_checkout_session(body: PortalCheckoutSessionCreate, customer: dict = Depends(get_current_customer)):
    """Create a Stripe Checkout Session for an invoice payment."""
    if not stripe_configured():
        raise HTTPException(503, "Stripe is not configured. Set STRIPE_SECRET_KEY in .env")

    invoice_id = body.invoice_id
    if not invoice_id:
        raise HTTPException(400, "invoice_id is required")

    rows = await _sql(f"SELECT * FROM invoices WHERE id = '{_safe_id(invoice_id)}' AND customer_id = '{customer['id']}'")
    if not rows:
        raise HTTPException(404, "Invoice not found")
    inv = rows[0]

    if inv.get("status") in ("paid", "cancelled"):
        raise HTTPException(400, f"Invoice is already {inv['status']}")

    total = float(inv.get("total", 0))
    payments = await _sql(f"SELECT * FROM payment WHERE invoice_id = '{_safe_id(invoice_id)}'")
    total_paid = sum(float(p.get("amount", 0)) for p in payments)
    amount_due = round(total - total_paid, 2)

    if amount_due <= 0:
        raise HTTPException(400, "Invoice is already fully paid")

    line_items = await _sql(f"SELECT * FROM invoice_line_items WHERE invoice_id = '{_safe_id(invoice_id)}'")
    items_desc = "; ".join(f"{li.get('description', '')} x{li.get('quantity', 1)}" for li in line_items)

    result = await create_checkout_session(
        invoice_id=invoice_id,
        invoice_number=int(inv.get("invoice_number", 0)),
        customer_id=customer["id"],
        customer_email=customer.get("email", ""),
        amount=amount_due,
        line_items_desc=items_desc,
    )

    if not result:
        raise HTTPException(502, "Failed to create Stripe checkout session")

    return result


# ── Saved Payment Methods (portal) ──────────────────────────────


@router.get("/api/portal/payment-methods")
async def portal_payment_methods(customer: dict = Depends(get_current_customer)):
    """List the customer's saved payment methods."""
    rows = await _sql(
        f"SELECT * FROM saved_payment_methods WHERE customer_id = '{customer['id']}'"
    )
    return {"payment_methods": _sort(rows, "created_at", desc=True)}


# ── Pay with Saved Card ─────────────────────────────────────────


@router.post("/api/portal/payments/pay-with-saved-card")
async def portal_pay_with_saved_card(
    body: PortalPayWithSavedCard,
    customer: dict = Depends(get_current_customer),
):
    """Pay an invoice using a saved payment method via Stripe PaymentIntent."""
    invoice_id = body.invoice_id
    payment_method_id = body.payment_method_id

    # Verify invoice belongs to customer
    rows = await _sql(f"SELECT * FROM invoices WHERE id = '{_safe_id(invoice_id)}' AND customer_id = '{customer['id']}'")
    if not rows:
        raise HTTPException(404, "Invoice not found")
    inv = rows[0]

    if inv.get("status") in ("paid", "cancelled"):
        raise HTTPException(400, f"Invoice is already {inv['status']}")

    # Verify payment method belongs to customer
    pm_rows = await _sql(
        f"SELECT * FROM saved_payment_methods WHERE stripe_payment_method_id = '{payment_method_id}' AND customer_id = '{customer['id']}'"
    )
    if not pm_rows:
        raise HTTPException(404, "Payment method not found")

    # Calculate amount due
    total = float(inv.get("total", 0))
    payments = await _sql(f"SELECT * FROM payment WHERE invoice_id = '{_safe_id(invoice_id)}'")
    total_paid = sum(float(p.get("amount", 0)) for p in payments)
    amount_due = round(total - total_paid, 2)

    if amount_due <= 0:
        raise HTTPException(400, "Invoice is already fully paid")

    # Create + confirm Stripe PaymentIntent
    if not stripe_configured():
        raise HTTPException(503, "Stripe is not configured. Set STRIPE_SECRET_KEY in .env")

    result = await create_payment_intent(
        invoice_id=invoice_id,
        invoice_number=int(inv.get("invoice_number", 0)),
        customer_email=customer.get("email", ""),
        amount=amount_due,
        payment_method_id=payment_method_id,
    )

    if not result or result.get("status") != "succeeded":
        error_detail = result.get("status", "unknown") if result else "no response"
        raise HTTPException(502, f"Stripe payment failed: {error_detail}")

    # Record payment
    await _call("record_payment", [
        customer.get("tenant_id", ""),
        invoice_id,
        customer["id"],
        amount_due,
        "card",
        result.get("payment_intent_id", ""),
        f"Stripe saved card payment — {result.get('payment_intent_id', '')}",
        "USD",
    ])

    # Update invoice status
    new_status = "paid"
    if new_status != inv.get("status"):
        await _call("update_invoice_status", [invoice_id, new_status])

    return {"ok": True, "payment_intent_id": result.get("payment_intent_id")}
