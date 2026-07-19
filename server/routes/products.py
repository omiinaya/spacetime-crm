"""Product + Inventory Adjustment routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from helpers import _safe_id, (
    _sql, _paginated, _call, _sort, _log_audit,
    require_role, logger,
)
from models import ProductCreate, ProductQuantityUpdate, InventoryAdjustmentCreate, StockTransferRequest
from mail import _notify_low_stock

router = APIRouter()


@router.get("/api/products")
async def list_products(search: str = "", category: str = "", offset: int = 0, limit: int = 50, user: dict = Depends(require_role("admin", "tech"))):
    """List products with pagination and optional search + category filter."""
    cat = category.strip()
    q = search.lower().strip()
    if q or cat:
        # When filtering, fetch up to 1000 rows, filter client-side, then paginate
        rows, _ = await _paginated(
            user["tenant_id"], "products",
            offset=0, limit=1000,
            order_by="name", order_desc=False,
        )
        if q:
            rows = [r for r in rows if q in (r.get("name") or "").lower() or q in (r.get("sku") or "").lower()]
        if cat:
            rows = [r for r in rows if r.get("category", "") == cat]
        total = len(rows)
        rows = rows[offset:offset + limit]
    else:
        rows, total = await _paginated(
            user["tenant_id"], "products",
            offset=offset, limit=limit,
            order_by="name", order_desc=False,
        )
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
        body.min_stock,
        body.location,
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


@router.put("/api/products/{product_id}")
async def update_product(product_id: str, body: ProductCreate, user: dict = Depends(require_role("admin", "tech"))):
    """Update product fields including min_stock."""
    await _call("update_product", [
        product_id,
        body.name,
        body.sku,
        body.barcode,
        body.description,
        body.category,
        body.price,
        body.cost,
        body.min_stock,
        body.location,
    ])
    await _log_audit(user, "update", "product", body.name, f"min_stock={body.min_stock}")
    return {"ok": True}


# ── INVENTORY ADJUSTMENT ──

@router.get("/api/products/{product_id}/adjustments")
async def get_product_adjustments(product_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql(f"SELECT * FROM inventory_adjustment WHERE product_id = '{_safe_id(product_id)}'")
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


@router.get("/api/products/low-stock")
async def list_low_stock(user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """List products below minimum stock threshold for the current tenant."""
    rows = await _sql(f"SELECT * FROM products WHERE tenant_id = '{_safe_id(user['tenant_id'])}'")
    low_stock = [
        r for r in rows
        if r.get("min_stock", 0) > 0 and r.get("quantity_on_hand", 0) <= r.get("min_stock", 0)
    ]
    return {"products": _sort(low_stock, "name"), "count": len(low_stock)}


@router.get("/api/products/by-barcode/{barcode}")
async def lookup_product_by_barcode(barcode: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """Find a product by barcode (exact match, tenant-scoped)."""
    rows = await _sql(f"SELECT * FROM products WHERE tenant_id = '{_safe_id(user['tenant_id'])}' AND barcode = '{_sanitize_sql(barcode)}'")
    if not rows:
        raise HTTPException(404, "Product not found for this barcode")
    return {"product": rows[0]}


@router.post("/api/products/low-stock/notify")
async def notify_low_stock(user: dict = Depends(require_role("admin"))):
    """Check low stock and send email alert to admin."""
    rows = await _sql(f"SELECT * FROM products WHERE tenant_id = '{user['tenant_id']}'")
    low_stock = [
        r for r in rows
        if r.get("min_stock", 0) > 0 and r.get("quantity_on_hand", 0) <= r.get("min_stock", 0)
    ]
    if not low_stock:
        return {"ok": True, "message": "No low stock items found", "count": 0}
    admin_email = user.get("email", "")
    if not admin_email:
        return {"ok": False, "error": "Admin user has no email configured"}
    _notify_low_stock(admin_email, low_stock)
    await _log_audit(user, "notify", "low_stock", "", f"products={len(low_stock)}")
    return {"ok": True, "count": len(low_stock), "notified": admin_email}


@router.post("/api/products/transfer")
async def transfer_stock(body: StockTransferRequest, user: dict = Depends(require_role("admin", "tech"))):
    """Transfer stock between two products. Creates inventory adjustments on both."""
    tid = user["tenant_id"]
    uid = user["id"]

    # Verify both products exist and belong to this tenant
    src_rows = await _sql(f"SELECT * FROM products WHERE id = '{_safe_id(body.source_product_id)}' AND tenant_id = '{tid}'")
    dst_rows = await _sql(f"SELECT * FROM products WHERE id = '{_safe_id(body.destination_product_id)}' AND tenant_id = '{tid}'")
    if not src_rows:
        raise HTTPException(404, "Source product not found")
    if not dst_rows:
        raise HTTPException(404, "Destination product not found")

    src = src_rows[0]
    qty = body.quantity

    if src.get("quantity_on_hand", 0) < qty:
        raise HTTPException(400, f"Insufficient stock: source has {src.get('quantity_on_hand', 0)}, need {qty}")

    ref = body.reference_id or f"transfer_{body.source_product_id[:8]}"

    # Negative adjustment on source
    await _call("create_inventory_adjustment", [tid, body.source_product_id, -qty, "transferred", ref, body.notes, uid])
    # Positive adjustment on destination
    await _call("create_inventory_adjustment", [tid, body.destination_product_id, qty, "transferred", ref, body.notes, uid])

    await _log_audit(user, "transfer", "stock", body.source_product_id, f"qty={qty}→{body.destination_product_id}")
    return {"ok": True, "quantity": qty, "reference": ref}


@router.get("/api/products/categories")
async def list_categories(user: dict = Depends(require_role("admin", "tech"))):
    """Get distinct product categories for the current tenant."""
    rows, _ = await _paginated(
        user["tenant_id"], "products",
        offset=0, limit=1000,
        order_by="name", order_desc=False,
    )
    cats = sorted({r.get("category", "") for r in rows if r.get("category")})
    return {"categories": cats}
