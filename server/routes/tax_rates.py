"""Tax Rate routes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends

from helpers import (

    _call,
    _log_audit,
    _paginated,
    require_role,
)
from rate_limit import limiter

from server.models.tax_rates import TaxRateCreate, TaxRateUpdate
router = APIRouter()


@router.get("/api/tax-rates")
async def list_tax_rates(
    offset: int = 0, limit: int = 50, user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """List tax rates with pagination."""
    rows, total = await _paginated(
        user["tenant_id"],
        "tax_rates",
        offset=offset,
        limit=limit,
        order_by="name",
        order_desc=False,
    )
    return {"tax_rates": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/api/tax-rates")
@limiter.limit("100/minute")
async def create_tax_rate(body: TaxRateCreate, user: Annotated[dict, Depends(require_role("admin"))]):
    await _call(
        "create_tax_rate",
        [
            user["tenant_id"],
            body.name,
            body.rate,
            body.is_default,
        ],
    )
    await _log_audit(user, "create", "tax_rate", body.name, f"rate={body.rate}")
    return {"ok": True}


@router.put("/api/tax-rates/{tax_id}")
@limiter.limit("100/minute")
async def update_tax_rate(tax_id: str, body: TaxRateUpdate, user: Annotated[dict, Depends(require_role("admin"))]):
    await _call(
        "update_tax_rate",
        [
            tax_id,
            body.name,
            body.rate,
            body.is_default,
        ],
    )
    await _log_audit(user, "update", "tax_rate", tax_id)
    return {"ok": True}


@router.delete("/api/tax-rates/{tax_id}")
@limiter.limit("100/minute")
async def delete_tax_rate(tax_id: str, user: Annotated[dict, Depends(require_role("admin"))]):
    await _call("delete_tax_rate", [tax_id])
    await _log_audit(user, "delete", "tax_rate", tax_id)
    return {"ok": True}
