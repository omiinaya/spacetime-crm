"""CSV Export/Import routes."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile

from helpers import (
    _call,
    _sql,
    require_role,
)
from rate_limit import limiter

router = APIRouter()

ENTITY_TABLE_MAP = {
    "customers": "customer",
    "tickets": "ticket",
    "invoices": "invoices",
    "payments": "payment",
    "appointments": "appointment",
    "products": "products",
    "estimates": "estimates",
    "purchase_orders": "purchase_order",
    "tax_rates": "tax_rate",
    "users": "user",
}


@router.get("/api/export/{entity}")
async def export_csv(entity: str, user: Annotated[dict, Depends(require_role("admin", "tech", "front_desk"))]):
    """Export all records of an entity type as CSV. Downloads as attachment."""
    table = ENTITY_TABLE_MAP.get(entity)
    if not table:
        raise HTTPException(400, f"Unknown entity: {entity}. Valid: {', '.join(ENTITY_TABLE_MAP)}")

    rows = await _sql(f"SELECT * FROM {table}")  # nosec - tenant_id from JWT or internal whitelist
    if not rows:
        return Response(
            content="",
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={entity}.csv"},
        )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={entity}.csv"},
    )


# ── CSV IMPORT ──


@router.post("/api/import/customers")
@limiter.limit("100/minute")
async def import_customers_csv(
    file: Annotated[UploadFile, File()], user: Annotated[dict, Depends(require_role("admin"))]
):
    """Import customers from CSV.
    Required: first_name, last_name. Optional: email, phone, etc.
    If id column provided, uses import_customer reducer to preserve IDs.
    """
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    if "first_name" not in (reader.fieldnames or []):
        raise HTTPException(400, "CSV must contain 'first_name' column")

    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    count = 0
    errors = []
    has_id = "id" in (reader.fieldnames or [])

    for i, row in enumerate(reader, start=2):
        try:
            fn = row.get("first_name", "").strip()
            ln = row.get("last_name", "").strip()
            email = row.get("email", "").strip()
            phone = row.get("phone", "").strip()
            mobile = row.get("mobile", "").strip()
            company = row.get("company", "").strip()
            addr1 = row.get("address_line1", "").strip()
            addr2 = row.get("address_line2", "").strip()
            city = row.get("city", "").strip()
            state = row.get("state", "").strip()
            zipc = row.get("zip", "").strip()
            notes = row.get("notes", "").strip()
            tags = row.get("tags", "").strip()

            if has_id and row.get("id", "").strip():
                cid = row["id"].strip()
                created_at = int(row.get("created_at", now_ms) or now_ms)
                updated_at = int(row.get("updated_at", now_ms) or now_ms)
                await _call(
                    "import_customer",
                    [
                        user["tenant_id"],
                        cid,
                        fn,
                        ln,
                        email,
                        phone,
                        mobile,
                        addr1,
                        addr2,
                        city,
                        state,
                        zipc,
                        company,
                        notes,
                        tags,
                        created_at,
                        updated_at,
                    ],
                )
            else:
                await _call("create_customer", [user["tenant_id"], fn, ln, email, phone])
            count += 1
        except Exception as e:
            errors.append(f"Row {i}: {e}")

    return {"imported": count, "errors": errors, "file": file.filename}


@router.post("/api/import/products")
@limiter.limit("100/minute")
async def import_products_csv(
    file: Annotated[UploadFile, File()], user: Annotated[dict, Depends(require_role("admin"))]
):
    """Import products from CSV.
    Required: name. Optional: sku, barcode, description, category, price, cost,
    quantity_on_hand, quantity_committed, min_stock, location, active.
    If id column provided, uses import_product reducer to preserve IDs.
    """
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    if "name" not in (reader.fieldnames or []):
        raise HTTPException(400, "CSV must contain 'name' column")

    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    count = 0
    errors = []
    has_id = "id" in (reader.fieldnames or [])

    for i, row in enumerate(reader, start=2):
        try:
            name = row.get("name", "").strip()
            sku = row.get("sku", "").strip()
            barcode = row.get("barcode", "").strip()
            desc = row.get("description", "").strip()
            category = row.get("category", "").strip()
            price = float(row.get("price", 0) or 0)
            cost = float(row.get("cost", 0) or 0)
            qoh = float(row.get("quantity_on_hand", 0) or 0)
            qc = float(row.get("quantity_committed", 0) or 0)
            min_stock = float(row.get("min_stock", 0) or 0)
            location = row.get("location", "").strip()
            active = (row.get("active", "true") or "true").strip().lower() in ("true", "1", "yes")

            if has_id and row.get("id", "").strip():
                pid = row["id"].strip()
                created_at = int(row.get("created_at", now_ms) or now_ms)
                updated_at = int(row.get("updated_at", now_ms) or now_ms)
                await _call(
                    "import_product",
                    [
                        user["tenant_id"],
                        pid,
                        name,
                        sku,
                        barcode,
                        desc,
                        category,
                        price,
                        cost,
                        qoh,
                        qc,
                        min_stock,
                        location,
                        active,
                        created_at,
                        updated_at,
                    ],
                )
            else:
                await _call(
                    "create_product",
                    [user["tenant_id"], name, sku, barcode, desc, category, price, cost, qoh, min_stock, location],
                )
            count += 1
        except Exception as e:
            errors.append(f"Row {i}: {e}")

    return {"imported": count, "errors": errors, "file": file.filename}
