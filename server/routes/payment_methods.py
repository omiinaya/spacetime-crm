"""Payment methods routes — saved cards for portal customers."""

from __future__ import annotations

import asyncio
from fastapi import APIRouter, Depends, HTTPException

from helpers import (
    _sql,
    _call,
    _sort,
    _log_audit,
    require_role,
    logger,
)
from models import SavePaymentMethodRequest, SetDefaultPaymentMethodRequest
from stripe_payments import create_setup_intent, is_configured
from rate_limit import limiter

router = APIRouter()


@router.get("/api/payment-methods")
async def list_payment_methods(
    customer_id: str = "",
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """List saved payment methods, optionally filtered by customer."""
    if customer_id:
        rows = await _sql(
            f"SELECT * FROM saved_payment_methods WHERE tenant_id = '{user['tenant_id']}' AND customer_id = '{customer_id}'"
        )
    else:
        rows = await _sql(f"SELECT * FROM saved_payment_methods WHERE tenant_id = '{user['tenant_id']}'")
    return {"payment_methods": _sort(rows, "created_at", desc=True)}


@router.post("/api/payment-methods/setup-intent")
@limiter.limit("100/minute")
async def create_payment_setup_intent(
    body: SetDefaultPaymentMethodRequest,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """Create a Stripe SetupIntent for securely collecting a payment method."""
    if not is_configured():
        raise HTTPException(400, "Stripe is not configured")
    result = await create_setup_intent(body.customer_id)
    if not result:
        raise HTTPException(500, "Failed to create SetupIntent")
    return result


@router.post("/api/payment-methods")
@limiter.limit("100/minute")
async def save_payment_method(
    body: SavePaymentMethodRequest,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """Save a payment method collected via Stripe SetupIntent."""
    await _call(
        "save_payment_method",
        [
            user["tenant_id"],
            body.customer_id,
            body.stripe_payment_method_id,
            body.brand,
            body.last4,
            body.exp_month,
            body.exp_year,
        ],
    )
    await _log_audit(user, "create", "payment_method", f"cust={body.customer_id} {body.brand} ****{body.last4}")
    return {"ok": True}


@router.put("/api/payment-methods/{method_id}/default")
@limiter.limit("100/minute")
async def set_default_payment_method(
    method_id: str,
    body: SetDefaultPaymentMethodRequest,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """Set a payment method as the default for a customer."""
    await _call("set_default_payment_method", [method_id, body.customer_id])
    await _log_audit(user, "update", "payment_method", method_id, "set as default")
    return {"ok": True}


@router.delete("/api/payment-methods/{method_id}")
@limiter.limit("100/minute")
async def delete_payment_method(
    method_id: str,
    user: dict = Depends(require_role("admin")),
):
    """Delete a saved payment method."""
    await _call("delete_payment_method", [method_id])
    await _log_audit(user, "delete", "payment_method", method_id)
    return {"ok": True}
