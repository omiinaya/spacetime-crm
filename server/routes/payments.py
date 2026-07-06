"""Payment routes."""
from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends

from config import settings
from helpers import (
    _sql, _paginated, _call, _log_audit, _fire_webhook,
    require_role, logger,
)
from models import PaymentCreate

router = APIRouter()


@router.get("/api/payments")
async def list_payments(invoice_id: str = "", offset: int = 0, limit: int = 50, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """List payments with pagination and optional invoice_id filter."""
    where = f"invoice_id = '{invoice_id}'" if invoice_id else ""
    rows, total = await _paginated(
        user["tenant_id"], "payment",
        offset=offset, limit=limit,
        where_extra=where,
        order_by="created_at", order_desc=True,
    )
    return {"payments": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/api/payments")
async def record_payment(body: PaymentCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    invoice_id = body.invoice_id
    await _call("record_payment", [
        user["tenant_id"],
        invoice_id,
        body.customer_id,
        body.amount,
        body.method,
        body.reference,
        body.notes,
        body.currency,
    ])
    if invoice_id:
        invoices = await _sql(f"SELECT * FROM invoices WHERE id = '{invoice_id}'")
        payments = await _sql(f"SELECT * FROM payment WHERE invoice_id = '{invoice_id}'")
        if invoices:
            inv = invoices[0]
            total_paid = sum(float(p.get("amount", 0)) for p in payments)
            inv_total = float(inv.get("total", 0))
            new_status = "paid" if total_paid >= inv_total else "partial" if total_paid > 0 else inv.get("status", "draft")
            if new_status != inv.get("status"):
                await _call("update_invoice_status", [invoice_id, new_status])

            async def _notify():
                from mail import _customer_email as _mail_customer_email, _notify_payment_received
                from sms import _customer_phone as _sms_customer_phone, _notify_payment_received as _sms_payment_received
                cust = await _sql(f"SELECT * FROM customer WHERE id = '{body.customer_id}'")
                email = _mail_customer_email(cust[0]) if cust else None
                if email:
                    link = f"{settings.app_url}/portal/"
                    _notify_payment_received(email, inv.get("invoice_number", 0), float(body.amount), link)
                phone = _sms_customer_phone(cust[0]) if cust else None
                if phone:
                    _sms_payment_received(phone, inv.get("invoice_number", 0), float(body.amount))
            asyncio.ensure_future(_notify())

    await _log_audit(user, "create", "payment", invoice_id, f"amount={body.amount}")
    asyncio.ensure_future(_fire_webhook("payment.created", {
        "entity_type": "payment",
        "invoice_id": invoice_id,
        "customer_id": body.customer_id,
        "amount": body.amount,
    }))
    return {"ok": True}


@router.delete("/api/payments/{payment_id}")
async def delete_payment(payment_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_payment", [payment_id])
    await _log_audit(user, "delete", "payment", payment_id)
    return {"ok": True}
