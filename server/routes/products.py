"""Product + Inventory Adjustment routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from helpers import (
    _sql, _paginated, _call, _sort, _log_audit,
    require_role, logger,
)
from models import ProductCreate, ProductQuantityUpdate, InventoryAdjustmentCreate

router = APIRouter()


@router.get("/api/products")
async def list_products(search: str = "", offset: int = 0, limit: int = 50, user: dict = Depends(require_role("admin", "tech"))):
    """List products with pagination and optional search."""
    rows, total = await _paginated(
        user["tenant_id"], "products",
        offset=offset, limit=limit,
        order_by="name", order_desc=False,
    )
    q = search.lower().strip()
    if q:
        rows = [
            r for r in rows
            if q in (r.get("name") or "").lower()
            or q in (r.get("sku") or "").lower()
        ]
        total = len(rows)
        rows = rows[offset:offset + limit]
    return {"products": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/api/products")
async def create_product(body: ProductCreate, user: dict = Depends(require_role("admin", "tech"))):
    await _call("create_product", [
        user["tenant_id"],
        body.name,
        body.sku,
        body.barcode,
        body.description,
        body.category,
        body.price,
        body.cost,
        body.quantity_on_hand,
    ])
    await _log_audit(user, "create", "product", body.name)
    return {"ok": True}


@router.put("/api/products/{product_id}/quantity")
async def update_product_quantity(product_id: str, body: ProductQuantityUpdate, user: dict = Depends(require_role("admin", "tech"))):
    await _call("update_product_quantity", [product_id, body.quantity_on_hand])
    await _log_audit(user, "update", "product_qty", product_id, f"qty={body.quantity_on_hand}")
    return {"ok": True}


@router.delete("/api/products/{product_id}")
async def delete_product(product_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_product", [product_id])
    await _log_audit(user, "delete", "product", product_id)
    return {"ok": True}


# ── INVENTORY ADJUSTMENT ──

@router.get("/api/products/{product_id}/adjustments")
async def get_product_adjustments(product_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql(f"SELECT * FROM inventory_adjustment WHERE product_id = '{product_id}'")
    return {"adjustments": _sort(rows, "created_at")}


@router.post("/api/products/{product_id}/adjustments")
async def create_adjustment(product_id: str, body: InventoryAdjustmentCreate, user: dict = Depends(require_role("admin", "tech"))):
    await _call("create_inventory_adjustment", [
        user["tenant_id"],
        product_id,
        body.quantity_change,
        body.reason,
        body.reference_id,
        body.notes,
        body.user_id,
    ])
    await _log_audit(user, "create", "adjustment", product_id, f"qty={body.quantity_change}")
    return {"ok": True}
