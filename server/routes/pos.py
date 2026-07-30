"""POS / Counter Sale routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from helpers import (
    _call,
    _log_audit,
    _paginated,
    _sql,
    jinja_env,
    require_role,
)
from models import POSAddItem, POSCreate
from pdf import html_to_pdf

router = APIRouter()


@router.get("/api/pos/sales")
async def list_pos_sales(
    offset: int = 0,
    limit: int = 50,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """List counter sales with pagination."""
    rows, total = await _paginated(
        user["tenant_id"],
        "counter_sale",
        offset=offset,
        limit=limit,
        order_by="created_at",
        order_desc=True,
    )
    return {"sales": rows, "total": total, "offset": offset, "limit": limit}


@router.get("/api/pos/sales/{sale_id}")
async def get_pos_sale(
    sale_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))
):
    """Get a single counter sale with line items."""
    rows = await _sql(
        f"SELECT * FROM counter_sale WHERE id = '{sale_id}' AND tenant_id = '{user['tenant_id']}'"
    )
    if not rows:
        raise HTTPException(404, "Sale not found")
    sale = rows[0]
    items = await _sql(f"SELECT * FROM counter_sale_line_item WHERE sale_id = '{sale_id}'")
    sale["line_items"] = sorted(items, key=lambda x: x.get("sort_order", 0))
    return {"sale": sale}


@router.get("/api/pos/sales/{sale_id}/receipt-pdf")
async def get_pos_receipt_pdf(
    sale_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))
):
    """Generate a printable PDF receipt for a completed counter sale."""
    rows = await _sql(
        f"SELECT * FROM counter_sale WHERE id = '{sale_id}' AND tenant_id = '{user['tenant_id']}'"
    )
    if not rows:
        raise HTTPException(404, "Sale not found")
    sale = rows[0]

    items = await _sql(f"SELECT * FROM counter_sale_line_item WHERE sale_id = '{sale_id}'")
    items = sorted(items, key=lambda x: x.get("sort_order", 0))

    receipt_number = sale.get("receipt_number", sale.get("id", "N/A"))
    ts = sale.get("created_at", 0) / 1000
    date_str = datetime.fromtimestamp(ts).strftime("%b %d, %Y %I:%M %p") if ts else "—"
    currency_sym = "$"
    if sale.get("currency") == "EUR":
        currency_sym = "\u20ac"
    elif sale.get("currency") == "GBP":
        currency_sym = "\u00a3"

    html = jinja_env.get_template("pos_receipt.html").render(
        store_name="SpacetimeCRM",
        store_address="123 Repair Shop Lane",
        store_phone="(555) 000-0000",
        store_tax_id="",
        receipt_number=receipt_number,
        date=date_str,
        customer_name=sale.get("customer_name", ""),
        items=[
            {
                "product_name": i.get("product_name", "Item"),
                "quantity": i.get("quantity", 1),
                "unit_price": float(i.get("unit_price", 0)),
                "total": float(i.get("total", 0)),
            }
            for i in items
        ],
        items_count=len(items),
        subtotal=float(sale.get("subtotal", 0)),
        discount_amount=float(sale.get("discount_amount", 0)),
        tax_rate=float(sale.get("tax_rate", 0)),
        tax_amount=float(sale.get("tax_amount", 0)),
        total=float(sale.get("total", 0)),
        currency=currency_sym,
        payment_method=sale.get("payment_method", "cash"),
        amount_tendered=float(sale.get("amount_tendered", 0)),
        change=float(sale.get("change", 0)),
    )

    pdf = await html_to_pdf(html)
    filename = f"receipt_{receipt_number}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.post("/api/pos/create")
async def create_pos_sale(
    body: POSCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))
):
    """Create a new counter sale (completed immediately)."""
    await _call(
        "create_counter_sale",
        [
            user["tenant_id"],
            body.customer_id,
            body.customer_name,
            body.payment_method,
            body.amount_tendered,
            body.tax_rate,
            body.discount_amount,
            body.currency,
        ],
    )
    await _log_audit(user, "create", "counter_sale", f"customer={body.customer_name}")
    return {"ok": True}


@router.post("/api/pos/items")
async def add_pos_item(
    body: POSAddItem, user: dict = Depends(require_role("admin", "tech", "front_desk"))
):
    """Add an item to a counter sale (recalculates totals)."""
    await _call(
        "add_counter_sale_item",
        [
            user["tenant_id"],
            body.sale_id,
            body.product_id,
            body.product_name,
            body.sku,
            body.quantity,
            body.unit_price,
        ],
    )
    return {"ok": True}


@router.post("/api/pos/refund/{sale_id}")
async def refund_pos_sale(sale_id: str, user: dict = Depends(require_role("admin"))):
    """Refund/void a counter sale."""
    await _call("refund_counter_sale", [sale_id])
    await _log_audit(user, "refund", "counter_sale", sale_id)
    return {"ok": True}


@router.delete("/api/pos/sales/{sale_id}")
async def delete_pos_sale(sale_id: str, user: dict = Depends(require_role("admin"))):
    """Delete a counter sale and its line items."""
    await _call("delete_counter_sale", [sale_id])
    await _log_audit(user, "delete", "counter_sale", sale_id)
    return {"ok": True}


@router.get("/api/pos/receipts")
async def list_receipts(
    offset: int = 0,
    limit: int = 50,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """List completed sales sorted by receipt number."""
    rows, total = await _paginated(
        user["tenant_id"],
        "counter_sale",
        offset=offset,
        limit=limit,
        where_extra="status = 'completed'",
        order_by="receipt_number",
        order_desc=True,
    )
    return {"receipts": rows, "total": total, "offset": offset, "limit": limit}
