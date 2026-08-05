"""Estimate routes."""

from __future__ import annotations

import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response

from pdf import html_to_pdf
from helpers import (
    _safe_id,
    _sql,
    _paginated,
    _call,
    _sort,
    _log_audit,
    _fire_webhook,
    require_role,
    jinja_env,
)
from models import EstimateCreate, EstimateStatusUpdate, EstimateLineItemCreate

# Estimate-specific status badge styles (estimates use draft/sent/approved/declined
# rather than the invoice paid/partial/overdue set).
_ESTIMATE_STATUS_LABELS = {
    "draft": "Draft",
    "sent": "Sent",
    "approved": "Approved",
    "declined": "Declined",
    "rejected": "Declined",
    "cancelled": "Cancelled",
}
_ESTIMATE_STATUS_CSS = {
    "draft": "draft",
    "sent": "sent",
    "approved": "approved",
    "declined": "declined",
    "rejected": "declined",
    "cancelled": "cancelled",
}
from sms import _customer_phone as _sms_customer_phone, _notify_estimate_approved as _sms_estimate_approved

router = APIRouter()


@router.get("/api/estimates")
async def list_estimates(
    status: str = "",
    offset: int = 0,
    limit: int = 50,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """List estimates with pagination and optional status filter."""
    where = f"status = '{status}'" if status else ""
    rows, total = await _paginated(
        user["tenant_id"],
        "estimates",
        offset=offset,
        limit=limit,
        where_extra=where,
        order_by="created_at",
        order_desc=True,
    )
    return {"estimates": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/api/estimates")
async def create_estimate(body: EstimateCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call(
        "create_estimate",
        [
            user["tenant_id"],
            body.customer_id,
            body.ticket_id,
            body.notes,
            body.expires_at,
            body.currency,
            body.tax_rate,
            body.discount_amount,
        ],
    )
    await _log_audit(user, "create", "estimate", f"cust={body.customer_id}")
    asyncio.ensure_future(
        _fire_webhook(
            "estimate.created",
            {
                "entity_type": "estimate",
                "customer_id": body.customer_id,
                "ticket_id": body.ticket_id,
            },
        )
    )
    return {"ok": True}


@router.put("/api/estimates/{estimate_id}/status")
async def update_estimate_status(
    estimate_id: str, body: EstimateStatusUpdate, user: dict = Depends(require_role("admin", "tech", "front_desk"))
):
    await _call("update_estimate_status", [estimate_id, body.status])
    await _log_audit(user, "update_status", "estimate", estimate_id, f"status={body.status}")
    return {"ok": True}


@router.get("/api/estimates/{estimate_id}/line-items")
async def get_estimate_line_items(estimate_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql(f"SELECT * FROM estimate_line_items WHERE estimate_id = '{_safe_id(estimate_id)}'")
    return {"line_items": _sort(rows, "sort_order", desc=False)}


@router.post("/api/estimates/{estimate_id}/line-items")
async def add_estimate_line_item(
    estimate_id: str, body: EstimateLineItemCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))
):
    await _call(
        "add_estimate_line_item",
        [
            estimate_id,
            body.item_type,
            body.description,
            body.quantity,
            body.unit_price,
        ],
    )
    await _log_audit(user, "create", "est_line_item", estimate_id, body.description)
    return {"ok": True}


@router.delete("/api/estimates/{estimate_id}")
async def delete_estimate(estimate_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_estimate", [estimate_id])
    await _log_audit(user, "delete", "estimate", estimate_id)
    return {"ok": True}


@router.post("/api/estimates/{estimate_id}/convert")
async def convert_estimate(estimate_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """Convert an approved estimate to an invoice (atomic reducer)."""
    est_rows = await _sql(f"SELECT * FROM estimates WHERE id = '{_safe_id(estimate_id)}'")
    if not est_rows:
        raise HTTPException(404, "Estimate not found")
    est = est_rows[0]
    if est.get("status") != "approved":
        raise HTTPException(400, "Only approved estimates can be converted")

    await _call("convert_estimate_to_invoice", [estimate_id])

    est_rows = await _sql(f"SELECT invoice_id FROM estimates WHERE id = '{_safe_id(estimate_id)}'")
    inv_id = est_rows[0].get("invoice_id", "") if est_rows else ""
    if not inv_id:
        raise HTTPException(500, "Failed to get generated invoice ID")

    await _log_audit(user, "convert", "estimate", estimate_id, f"invoice_id={inv_id}")

    asyncio.ensure_future(
        _fire_webhook(
            "estimate.approved",
            {
                "entity_type": "estimate",
                "id": estimate_id,
                "customer_id": est.get("customer_id", ""),
                "total": est.get("total", 0),
                "invoice_id": inv_id,
            },
        )
    )

    async def _sms_notify():
        cust = await _sql(f"SELECT * FROM customer WHERE id = '{_safe_id(est.get('customer_id', ''))}'")
        phone = _sms_customer_phone(cust[0]) if cust else None
        if phone:
            _sms_estimate_approved(phone, est.get("estimate_number", 0), float(est.get("total", 0)))

    asyncio.ensure_future(_sms_notify())

    return {"ok": True, "invoice_id": inv_id}


@router.get("/api/estimates/{estimate_id}/pdf")
async def estimate_pdf(estimate_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """Generate a downloadable PDF for an estimate."""
    ests = await _sql(f"SELECT * FROM estimates WHERE id = '{_safe_id(estimate_id)}'")
    if not ests:
        raise HTTPException(404, "Estimate not found")
    est = ests[0]
    items = await _sql(f"SELECT * FROM estimate_line_items WHERE estimate_id = '{_safe_id(estimate_id)}'")
    items = _sort(items, "sort_order", desc=False)
    cust = await _sql(f"SELECT * FROM customer WHERE id = '{_safe_id(est['customer_id'])}'")

    customer = cust[0] if cust else {}
    status = est.get("status", "draft")
    ts = est.get("created_at", 0) / 1000
    expires = est.get("expires_at", 0) / 1000

    template = jinja_env.get_template("estimate.html")
    html = template.render(
        status=_ESTIMATE_STATUS_CSS.get(status, "draft"),
        status_label=_ESTIMATE_STATUS_LABELS.get(status, status.capitalize()),
        estimate_number=est.get("estimate_number", ""),
        customer_name=f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or "—",
        customer_company=customer.get("company", ""),
        customer_address=", ".join(
            filter(
                None,
                [
                    customer.get("address_line1", ""),
                    customer.get("city", ""),
                    customer.get("state", ""),
                ],
            )
        ),
        customer_email=customer.get("email", ""),
        customer_phone=customer.get("phone", ""),
        date=datetime.fromtimestamp(ts).strftime("%b %d, %Y") if ts else "—",
        expires_date=datetime.fromtimestamp(expires).strftime("%b %d, %Y") if expires else "",
        currency=est.get("currency", "USD"),
        subtotal=f"{float(est.get('subtotal', 0)):.2f}",
        total=f"{float(est.get('total', 0)):.2f}",
        tax_amount=f"{float(est.get('tax_amount', 0)):.2f}",
        tax_rate=f"{float(est.get('tax_rate', 0)) * 100:.1f}",
        discount_amount=float(est.get("discount_amount", 0)),
        notes=est.get("notes", ""),
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
    filename = f"estimate_{est.get('estimate_number', 'unknown')}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
