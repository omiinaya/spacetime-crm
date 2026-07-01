"""Invoice routes."""
from __future__ import annotations

import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from pdf import html_to_pdf

from helpers import (
    _sql, _paginated, _call, _sort, _log_audit, _fire_webhook,
    require_role, logger, STATUS_LABELS, STATUS_CSS, jinja_env,
)
from models import InvoiceCreate, InvoiceStatusUpdate, InvoiceLineItemCreate, InvoiceTaxRateUpdate, BulkInvoiceStatusUpdate

router = APIRouter()


@router.get("/api/invoices")
async def list_invoices(status: str = "", offset: int = 0, limit: int = 50, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """List invoices with pagination and optional status filter."""
    where = f"status = '{status}'" if status else ""
    rows, total = await _paginated(
        user["tenant_id"], "invoices",
        offset=offset, limit=limit,
        where_extra=where,
        order_by="created_at", order_desc=True,
    )
    return {"invoices": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/api/invoices")
async def create_invoice(body: InvoiceCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("create_invoice", [
        user["tenant_id"],
        body.customer_id,
        body.ticket_id,
        body.notes,
        body.terms,
        body.due_date,
        body.currency,
    ])

    async def _notify():
        cust = await _sql(f"SELECT * FROM customer WHERE id = '{body.customer_id}'")
        from mail import _customer_email as _mail_customer_email
        from mail import _notify_invoice_created
        from sms import _customer_phone as _sms_customer_phone
        from sms import _notify_invoice_created as _sms_invoice_created
        email = _mail_customer_email(cust[0]) if cust else None
        if email:
            invs = await _sql("SELECT * FROM invoices LIMIT 1")
            if invs:
                inv = invs[0]
                link = f"http://localhost:8723/portal/"
                _notify_invoice_created(email, inv.get("invoice_number", 0), float(inv.get("total", 0)), link)
        phone = _sms_customer_phone(cust[0]) if cust else None
        if phone:
            invs = await _sql("SELECT * FROM invoices LIMIT 1")
            if invs:
                inv = invs[0]
                _sms_invoice_created(phone, inv.get("invoice_number", 0), float(inv.get("total", 0)))
    asyncio.ensure_future(_notify())

    await _log_audit(user, "create", "invoice", f"cust={body.customer_id}")
    asyncio.ensure_future(_fire_webhook("invoice.created", {
        "entity_type": "invoice",
        "customer_id": body.customer_id,
        "ticket_id": body.ticket_id,
    }))
    return {"ok": True}


@router.get("/api/invoices/summary")
async def get_invoice_summary(user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """Get invoice summary: counts and totals by status."""
    rows = await _sql(f"SELECT * FROM invoices WHERE tenant_id = '{user['tenant_id']}'")
    now = int(datetime.utcnow().timestamp() * 1000)
    summary: dict[str, dict] = {}
    for inv in rows:
        s = inv.get("status", "draft")
        total = float(inv.get("total", 0))
        if s not in summary:
            summary[s] = {"count": 0, "total": 0.0}
        summary[s]["count"] += 1
        summary[s]["total"] = round(summary[s]["total"] + total, 2)
    # Add on-the-fly overdue detection
    sent_partial_overdue = sum(
        1 for i in rows
        if i.get("status") in ("sent", "partial") and i.get("due_date", 0) > 0 and i.get("due_date", 0) < now
    )
    sent_partial_overdue_total = round(sum(
        float(i.get("total", 0)) for i in rows
        if i.get("status") in ("sent", "partial") and i.get("due_date", 0) > 0 and i.get("due_date", 0) < now
    ), 2)
    return {
        "by_status": summary,
        "total_count": len(rows),
        "total_revenue": round(sum(float(i.get("total", 0)) for i in rows if i.get("status") == "paid"), 2),
        "total_outstanding": round(sum(float(i.get("total", 0)) for i in rows if i.get("status") in ("sent", "partial", "overdue")), 2),
        "overdue_count": sent_partial_overdue + summary.get("overdue", {}).get("count", 0),
        "overdue_total": round(sent_partial_overdue_total + summary.get("overdue", {}).get("total", 0), 2),
    }


@router.post("/api/invoices/bulk-status-update")
async def bulk_update_invoice_status(body: BulkInvoiceStatusUpdate, user: dict = Depends(require_role("admin"))):
    """Update status of multiple invoices at once."""
    updated = 0
    errors = 0
    for inv_id in body.invoice_ids:
        try:
            await _call("update_invoice_status", [inv_id, body.status])
            updated += 1
        except HTTPException:
            errors += 1
    if updated:
        await _log_audit(user, "bulk_update_status", "invoice", f"count={updated}", f"status={body.status}")
        asyncio.ensure_future(_fire_webhook("invoice.bulk_status_changed", {
            "entity_type": "invoice",
            "count": updated,
            "status": body.status,
        }))
    return {"ok": True, "updated": updated, "errors": errors}


@router.get("/api/invoices/overdue-count")
async def get_overdue_count(user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """Get count of overdue invoices and total overdue amount.
    Detects overdue on-the-fly: invoices past due_date with status sent/partial count as overdue."""
    rows = await _sql(f"SELECT * FROM invoices WHERE tenant_id = '{user['tenant_id']}' AND (status = 'overdue' OR ((status = 'sent' OR status = 'partial') AND due_date > 0 AND due_date < {int(datetime.utcnow().timestamp() * 1000)}))")
    total = sum(float(i.get("total", 0)) for i in rows)
    return {"count": len(rows), "total": round(total, 2)}


@router.post("/api/invoices/trigger-overdue-check")
async def trigger_overdue_check(user: dict = Depends(require_role("admin"))):
    """Mark overdue invoices — checks each sent/partial invoice past its due date
    and updates status to 'overdue' via the STDB reducer, or reports it would mark them."""
    # Detect overdue invoices that need marking
    now = int(datetime.utcnow().timestamp() * 1000)
    rows = await _sql(f"SELECT * FROM invoices WHERE tenant_id = '{user['tenant_id']}' AND (status = 'sent' OR status = 'partial') AND due_date > 0 AND due_date < {now}")
    marked = 0
    for inv in rows:
        try:
            await _call("update_invoice_status", [inv["id"], "overdue"])
            marked += 1
        except HTTPException:
            pass
    return {"ok": True, "marked": marked}


@router.post("/api/invoices/send-overdue-reminders")
async def send_overdue_reminders(user: dict = Depends(require_role("admin"))):
    """Find overdue invoices and send email/SMS reminders to each customer."""
    now = int(datetime.utcnow().timestamp() * 1000)
    rows = await _sql(f"SELECT * FROM invoices WHERE tenant_id = '{user['tenant_id']}' AND (status = 'overdue' OR ((status = 'sent' OR status = 'partial') AND due_date > 0 AND due_date < {now}))")
    sent = {"email": 0, "sms": 0, "total": 0}
    for inv in rows:
        cust = await _sql(f"SELECT * FROM customer WHERE id = '{inv['customer_id']}'")
        if not cust:
            continue
        c = cust[0]
        email = c.get("email") or None
        phone = c.get("phone") or None
        due_ts = inv.get("due_date", 0) / 1000
        due_str = datetime.fromtimestamp(due_ts).strftime("%b %d, %Y") if due_ts else "—"
        link = f"http://localhost:8723/portal/"
        inv_num = inv.get("invoice_number", 0)
        total = float(inv.get("total", 0))

        if email:
            from mail import _notify_overdue_reminder as _mail_reminder
            _mail_reminder(email, inv_num, total, due_str, link)
            sent["email"] += 1
        if phone:
            from sms import _notify_overdue_reminder as _sms_reminder
            _sms_reminder(phone, inv_num, total)
            sent["sms"] += 1
        sent["total"] += 1

    await _log_audit(user, "send_overdue_reminders", "invoice", f"email={sent['email']} sms={sent['sms']}")
    return {"ok": True, **sent}


@router.put("/api/invoices/{invoice_id}/status")
async def update_invoice_status(invoice_id: str, body: InvoiceStatusUpdate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("update_invoice_status", [invoice_id, body.status])
    new_status = body.status
    await _log_audit(user, "update_status", "invoice", invoice_id, f"status={new_status}")
    asyncio.ensure_future(_fire_webhook("invoice.status_changed" if new_status != "paid" else "invoice.paid", {
        "entity_type": "invoice",
        "id": invoice_id,
        "status": new_status,
    }))
    return {"ok": True}


@router.get("/api/invoices/{invoice_id}/line-items")
async def get_invoice_line_items(invoice_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql(f"SELECT * FROM invoice_line_items WHERE invoice_id = '{invoice_id}'")
    return {"line_items": _sort(rows, "sort_order", desc=False)}


@router.post("/api/invoices/{invoice_id}/line-items")
async def add_invoice_line_item(invoice_id: str, body: InvoiceLineItemCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("add_invoice_line_item", [
        invoice_id,
        body.item_type,
        body.description,
        body.quantity,
        body.unit_price,
    ])
    await _log_audit(user, "create", "line_item", invoice_id, body.description)
    return {"ok": True}


@router.delete("/api/invoices/{invoice_id}/line-items/{item_id}")
async def delete_invoice_line_item(invoice_id: str, item_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_invoice_line_item", [item_id])
    await _log_audit(user, "delete", "line_item", invoice_id)
    return {"ok": True}


@router.delete("/api/invoices/{invoice_id}")
async def delete_invoice(invoice_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_invoice", [invoice_id])
    await _log_audit(user, "delete", "invoice", invoice_id)
    return {"ok": True}


@router.put("/api/invoices/{invoice_id}/tax-rate")
async def set_invoice_tax_rate(invoice_id: str, body: InvoiceTaxRateUpdate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("set_invoice_tax_rate", [invoice_id, body.tax_rate])
    await _log_audit(user, "update", "invoice_tax", invoice_id, f"rate={body.tax_rate}")
    return {"ok": True}


@router.get("/api/invoices/{invoice_id}/pdf")
async def invoice_pdf(invoice_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    invs = await _sql(f"SELECT * FROM invoices WHERE id = '{invoice_id}'")
    if not invs:
        raise HTTPException(404, "Invoice not found")
    inv = invs[0]
    items = await _sql(f"SELECT * FROM invoice_line_items WHERE invoice_id = '{invoice_id}'")
    items = _sort(items, "sort_order", desc=False)
    cust = await _sql(f"SELECT * FROM customer WHERE id = '{inv['customer_id']}'")

    customer = cust[0] if cust else {}
    status = inv.get("status", "draft")
    ts = inv.get("created_at", 0) / 1000
    due = inv.get("due_date", 0) / 1000

    template = jinja_env.get_template("invoice.html")
    html = template.render(
        status=STATUS_CSS.get(status, "draft"),
        status_label=STATUS_LABELS.get(status, status.capitalize()),
        invoice_number=inv.get("invoice_number", ""),
        customer_name=f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or "—",
        customer_company=customer.get("company", ""),
        customer_address=", ".join(filter(None, [
            customer.get("address_line1", ""),
            customer.get("city", ""),
            customer.get("state", ""),
        ])),
        customer_email=customer.get("email", ""),
        customer_phone=customer.get("phone", ""),
        date=datetime.fromtimestamp(ts).strftime("%b %d, %Y") if ts else "—",
        due_date=datetime.fromtimestamp(due).strftime("%b %d, %Y") if due else "—",
        terms=inv.get("terms", ""),
        notes=inv.get("notes", ""),
        subtotal=f"{float(inv.get('subtotal', 0)):.2f}",
        total=f"{float(inv.get('total', 0)):.2f}",
        tax_amount=f"{float(inv.get('tax_amount', 0)):.2f}",
        tax_rate=f"{float(inv.get('tax_rate', 0)) * 100:.1f}",
        discount_amount=float(inv.get("discount_amount", 0)),
        items=[
            {
                "description": i.get("description", ""),
                "quantity": i.get("quantity", 1),
                "unit_price": f"{float(i.get('unit_price', 0)):.2f}",
                "total": f"{float(i.get('total', 0)):.2f}",
            }
            for i in items
        ],
    )

    pdf = await html_to_pdf(html)
    filename = f"invoice_{inv.get('invoice_number', 'unknown')}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
