"""Estimate routes."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, HTTPException

from helpers import (
    _call,
    _fire_webhook,
    _log_audit,
    _paginated,
    _safe_id,
    _sort,
    _sql,
    require_role,
)
from rate_limit import limiter
from sms import _customer_phone as _sms_customer_phone
from sms import _notify_estimate_approved as _sms_estimate_approved

if TYPE_CHECKING:
    from models import EstimateCreate, EstimateLineItemCreate, EstimateStatusUpdate

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
@limiter.limit("100/minute")
async def create_estimate(body: EstimateCreate, user: Annotated[dict, Depends(require_role("admin", "tech", "front_desk"))]):
    await _call(
        "create_estimate",
        [
            user["tenant_id"],
            body.customer_id,
            body.ticket_id,
            body.notes,
            body.expires_at,
            body.currency,
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
        ),
    )
    return {"ok": True}


@router.put("/api/estimates/{estimate_id}/status")
@limiter.limit("100/minute")
async def update_estimate_status(
    estimate_id: str, body: EstimateStatusUpdate, user: Annotated[dict, Depends(require_role("admin", "tech", "front_desk"))],
):
    await _call("update_estimate_status", [estimate_id, body.status])
    await _log_audit(user, "update_status", "estimate", estimate_id, f"status={body.status}")
    return {"ok": True}


@router.get("/api/estimates/{estimate_id}/line-items")
async def get_estimate_line_items(estimate_id: str, user: Annotated[dict, Depends(require_role("admin", "tech", "front_desk"))]):
    rows = await _sql(f"SELECT * FROM estimate_line_items WHERE estimate_id = '{_safe_id(estimate_id)}'")
    return {"line_items": _sort(rows, "sort_order", desc=False)}


@router.post("/api/estimates/{estimate_id}/line-items")
@limiter.limit("100/minute")
async def add_estimate_line_item(
    estimate_id: str, body: EstimateLineItemCreate, user: Annotated[dict, Depends(require_role("admin", "tech", "front_desk"))],
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
@limiter.limit("100/minute")
async def delete_estimate(estimate_id: str, user: Annotated[dict, Depends(require_role("admin"))]):
    await _call("delete_estimate", [estimate_id])
    await _log_audit(user, "delete", "estimate", estimate_id)
    return {"ok": True}


@router.post("/api/estimates/{estimate_id}/convert")
@limiter.limit("100/minute")
async def convert_estimate(estimate_id: str, user: Annotated[dict, Depends(require_role("admin", "tech", "front_desk"))]):
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
        ),
    )

    async def _sms_notify() -> None:
        cust = await _sql(f"SELECT * FROM customer WHERE id = '{_safe_id(est.get('customer_id', ''))}'")
        phone = _sms_customer_phone(cust[0]) if cust else None
        if phone:
            _sms_estimate_approved(phone, est.get("estimate_number", 0), float(est.get("total", 0)))

    asyncio.ensure_future(_sms_notify())

    return {"ok": True, "invoice_id": inv_id}
