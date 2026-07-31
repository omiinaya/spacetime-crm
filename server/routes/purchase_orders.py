"""Purchase Order routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from helpers import (
    _call,
    _log_audit,
    _paginated,
    _sort,
    _sql,
    _sqlesc,
    require_role,
)
from models import (
    POApprovalAction,
    POLineItemCreate,
    POReceiveItem,
    PurchaseOrderCreate,
    PurchaseOrderStatusUpdate,
)

router = APIRouter()


@router.get("/api/purchase-orders")
async def list_purchase_orders(
    offset: int = 0,
    limit: int = 50,
    user: dict = Depends(require_role("admin", "tech")),
):
    """List purchase orders with pagination."""
    rows, total = await _paginated(
        user["tenant_id"],
        "purchase_order",
        offset=offset,
        limit=limit,
        order_by="created_at",
        order_desc=True,
    )
    return {"purchase_orders": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/api/purchase-orders")
async def create_purchase_order(
    body: PurchaseOrderCreate,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    await _call(
        "create_purchase_order",
        [
            user["tenant_id"],
            body.vendor_name,
            body.notes,
            body.currency,
        ],
    )
    await _log_audit(user, "create", "purchase_order", body.vendor_name)
    return {"ok": True}


@router.delete("/api/purchase-orders/{po_id}")
async def delete_purchase_order(po_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_purchase_order", [po_id])
    await _log_audit(user, "delete", "purchase_order", po_id)
    return {"ok": True}


@router.get("/api/purchase-orders/{po_id}")
async def get_purchase_order(
    po_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))
):
    rows = await _sql(
        f"SELECT * FROM purchase_order WHERE id = '{_sqlesc(po_id)}' AND tenant_id = '{_sqlesc(user['tenant_id'])}'"
    )
    if not rows:
        raise HTTPException(404, "Purchase order not found")
    po = rows[0]
    items = await _sql(
        f"SELECT * FROM purchase_order_line_item WHERE purchase_order_id = '{_sqlesc(po_id)}' AND tenant_id = '{_sqlesc(user['tenant_id'])}'"
    )
    po["line_items"] = _sort(items, "description", desc=False)
    total_qty = sum(float(i.get("quantity", 0)) for i in items)
    total_received = sum(float(i.get("received_quantity", 0)) for i in items)
    po["receipt_progress"] = round((total_received / total_qty * 100) if total_qty > 0 else 0, 1)
    return {"purchase_order": po}


@router.post("/api/purchase-orders/{po_id}/line-items")
async def add_po_line_item(
    po_id: str,
    body: POLineItemCreate,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    await _call(
        "add_po_line_item",
        [
            po_id,
            body.product_id,
            body.description,
            body.quantity,
            body.unit_price,
        ],
    )
    await _log_audit(user, "create", "po_line_item", po_id, body.description)
    return {"ok": True}


@router.delete("/api/purchase-orders/{po_id}/line-items/{item_id}")
async def delete_po_line_item(
    po_id: str, item_id: str, user: dict = Depends(require_role("admin"))
):
    await _call("delete_po_line_item", [po_id, item_id])
    await _log_audit(user, "delete", "po_line_item", po_id)
    return {"ok": True}


@router.put("/api/purchase-orders/{po_id}/status")
async def update_po_status(
    po_id: str,
    body: PurchaseOrderStatusUpdate,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    await _call("update_po_status", [po_id, body.status])
    await _log_audit(user, "update_status", "purchase_order", po_id, f"status={body.status}")
    return {"ok": True}


@router.post("/api/purchase-orders/{po_id}/receive")
async def receive_po_items(
    po_id: str,
    body: POReceiveItem,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """Receive multiple items on a PO at once.
    Body: { items: [{ id: string, received_quantity: number }] }
    """
    items = body.items
    for item in items:
        await _call("receive_po_item", [item["id"], item.get("received_quantity", 0)])
    await _log_audit(user, "receive", "purchase_order", po_id, f"{len(items)} items")
    return {"ok": True}


@router.post("/api/purchase-orders/{po_id}/submit-for-approval")
async def submit_po_for_approval(
    po_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))
):
    """Submit a draft PO for approval."""
    await _call("submit_for_approval", [po_id])
    await _log_audit(user, "submit_approval", "purchase_order", po_id)
    return {"ok": True}


@router.post("/api/purchase-orders/{po_id}/approve")
async def approve_purchase_order(
    po_id: str, body: POApprovalAction, user: dict = Depends(require_role("admin"))
):
    """Approve a pending PO."""
    await _call("approve_po", [po_id, body.user_id])
    await _log_audit(user, "approve", "purchase_order", po_id, f"approver={body.user_id}")
    return {"ok": True}


@router.post("/api/purchase-orders/{po_id}/reject")
async def reject_purchase_order(po_id: str, user: dict = Depends(require_role("admin"))):
    """Reject a pending PO, sending it back to draft."""
    await _call("reject_po", [po_id])
    await _log_audit(user, "reject", "purchase_order", po_id)
    return {"ok": True}
