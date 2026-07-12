"""Customer routes."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Annotated

import bcrypt
from fastapi import APIRouter, Depends, HTTPException

from client import get_http_client
from helpers import (
    CUSTOMER_SENSITIVE_FIELDS,
    _call,
    _fire_webhook,
    _log_audit,
    _paginated,
    _safe_customer,
    _safe_id,
    _sql,
    _sql_t,
    require_role,
)
from rate_limit import limiter

if TYPE_CHECKING:
    from models import CustomerCreate, CustomerUpdate, SetPasswordRequest

router = APIRouter()


@router.get("/api/customers")
async def list_customers(
    search: str = "",
    offset: int = 0,
    limit: int = 50,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """List customers with pagination and optional search."""
    rows, total = await _paginated(
        user["tenant_id"],
        "customer",
        offset=offset,
        limit=limit,
        order_by="created_at",
        order_desc=True,
        sensitive_fields=CUSTOMER_SENSITIVE_FIELDS,
    )
    q = search.lower().strip()
    if q:
        rows = [
            r
            for r in rows
            if q in (r.get("first_name") or "").lower()
            or q in (r.get("last_name") or "").lower()
            or q in (r.get("email") or "").lower()
            or q in (r.get("phone") or "")
        ]
        total = len(rows)
        rows = rows[offset : offset + limit]
    rows = [_safe_customer(r) for r in rows]
    return {"customers": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/api/customers")
@limiter.limit("100/minute")
async def create_customer(body: CustomerCreate, user: Annotated[dict, Depends(require_role("admin", "tech", "front_desk"))]):
    await _call(
        "create_customer",
        [
            user["tenant_id"],
            body.first_name,
            body.last_name,
            body.email,
            body.phone,
        ],
    )
    details = f"{body.first_name} {body.last_name}".strip()
    await _log_audit(user, "create", "customer", details, f"email={body.email}")
    asyncio.ensure_future(
        _fire_webhook(
            "customer.created",
            {
                "entity_type": "customer",
                "name": details,
                "email": body.email,
            },
        ),
    )
    return {"ok": True}


@router.put("/api/customers/{customer_id}")
@limiter.limit("100/minute")
async def update_customer(
    customer_id: str, body: CustomerUpdate, user: Annotated[dict, Depends(require_role("admin", "tech", "front_desk"))],
):
    await _call(
        "update_customer",
        [
            customer_id,
            body.first_name,
            body.last_name,
            body.email,
            body.phone,
            body.mobile,
            body.address_line1,
            body.address_line2,
            body.city,
            body.state,
            body.zip,
            body.company,
            body.notes,
            body.tags,
        ],
    )
    await _log_audit(user, "update", "customer", customer_id)
    asyncio.ensure_future(
        _fire_webhook(
            "customer.updated",
            {
                "entity_type": "customer",
                "id": customer_id,
            },
        ),
    )
    return {"ok": True}


@router.delete("/api/customers/{customer_id}")
@limiter.limit("100/minute")
async def delete_customer(customer_id: str, user: Annotated[dict, Depends(require_role("admin"))]):
    await _call("delete_customer", [customer_id])
    await _log_audit(user, "delete", "customer", customer_id)
    asyncio.ensure_future(
        _fire_webhook(
            "customer.deleted",
            {
                "entity_type": "customer",
                "id": customer_id,
            },
        ),
    )
    return {"ok": True}


@router.post("/api/customers/{customer_id}/portal-password")
@limiter.limit("100/minute")
async def set_customer_portal_password(
    customer_id: str, body: SetPasswordRequest, user: Annotated[dict, Depends(require_role("admin"))],
):
    """Admin sets/resets a customer's portal password."""
    pw = body.password
    if len(pw) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    await _call("set_customer_password", [customer_id, hashed])
    await _log_audit(user, "update", "customer_portal_password", customer_id)
    return {"ok": True}


# ── CUSTOMER GEOLOCATION ──


@router.get("/api/customers/geolocations")
async def list_customer_geolocations(user: Annotated[dict, Depends(require_role("admin", "tech", "front_desk"))]):
    """Return all customers with their geolocation data for the map."""
    customers = await _sql_t("SELECT * FROM customer", user["tenant_id"])
    geos = await _sql_t("SELECT * FROM customer_geolocations", user["tenant_id"])
    geo_map = {g["customer_id"]: g for g in geos}
    result = []
    for c in customers:
        c = _safe_customer(c)
        loc = geo_map.get(c["id"])
        full_name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
        addr_parts = [c.get("address_line1", ""), c.get("city", ""), c.get("state", ""), c.get("zip", "")]
        address = ", ".join(a for a in addr_parts if a)
        result.append(
            {
                "id": c["id"],
                "name": full_name,
                "company": c.get("company", ""),
                "email": c.get("email", ""),
                "phone": c.get("phone", ""),
                "address": address,
                "address_line1": c.get("address_line1", ""),
                "city": c.get("city", ""),
                "state": c.get("state", ""),
                "zip": c.get("zip", ""),
                "latitude": loc["latitude"] if loc else None,
                "longitude": loc["longitude"] if loc else None,
                "has_location": loc is not None,
            },
        )
    return {"locations": result}


@router.post("/api/customers/{customer_id}/geocode")
@limiter.limit("100/minute")
async def geocode_customer(customer_id: str, user: Annotated[dict, Depends(require_role("admin", "tech"))]):
    """Geocode a single customer's address and store the location."""
    customers = await _sql(f"SELECT * FROM customer WHERE id = '{_safe_id(customer_id)}'")
    if not customers:
        raise HTTPException(404, "Customer not found")
    c = customers[0]
    addr_parts = [c.get("address_line1", ""), c.get("city", ""), c.get("state", ""), c.get("zip", "")]
    address = ", ".join(a for a in addr_parts if a)
    if not address:
        raise HTTPException(400, "Customer has no address to geocode")

    client = get_http_client()
    resp = await client.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": address, "format": "json", "limit": 1},
        headers={"User-Agent": "SpacetimeCRM/1.0"},
        timeout=15,
    )
    if resp.status_code >= 400:
        raise HTTPException(502, f"Geocoding failed: {resp.text[:200]}")
    data = resp.json()
    if not data:
        return {"ok": False, "error": "No geocoding result found for address"}

    lat = float(data[0]["lat"])
    lng = float(data[0]["lon"])
    await _call("set_customer_geolocation", [user["tenant_id"], customer_id, lat, lng])
    return {"ok": True, "latitude": lat, "longitude": lng, "display_name": data[0].get("display_name", "")}


@router.post("/api/customers/geocode-all")
@limiter.limit("100/minute")
async def geocode_all_customers(user: Annotated[dict, Depends(require_role("admin", "tech"))]):
    """Geocode all customers that don't have coordinates yet."""
    customers = await _sql_t("SELECT * FROM customer", user["tenant_id"])
    existing = await _sql_t("SELECT * FROM customer_geolocations", user["tenant_id"])
    existing_ids = {e["customer_id"] for e in existing}
    results = {"geocoded": 0, "failed": 0, "skipped": 0}

    for c in customers:
        if c["id"] in existing_ids:
            results["skipped"] += 1
            continue
        addr_parts = [c.get("address_line1", ""), c.get("city", ""), c.get("state", ""), c.get("zip", "")]
        address = ", ".join(a for a in addr_parts if a)
        if not address:
            results["skipped"] += 1
            continue
        try:
            client = get_http_client()
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1},
                headers={"User-Agent": "SpacetimeCRM/1.0"},
                timeout=10,
            )
            if resp.status_code >= 400:
                results["failed"] += 1
                continue
            data = resp.json()
            if data:
                await _call(
                    "set_customer_geolocation",
                    [
                        user["tenant_id"],
                        c["id"],
                        float(data[0]["lat"]),
                        float(data[0]["lon"]),
                    ],
                )
                results["geocoded"] += 1
            else:
                results["failed"] += 1
        except Exception:
            results["failed"] += 1

    return results


@router.get("/api/customers/duplicates")
async def find_duplicate_customers(user: Annotated[dict, Depends(require_role("admin"))]):
    """Find potential duplicate customers by matching email or phone."""
    rows = await _sql_t("SELECT * FROM customer", user["tenant_id"])
    seen_email: dict[str, list[dict]] = {}
    seen_phone: dict[str, list[dict]] = {}
    for c in rows:
        email = (c.get("email") or "").strip().lower()
        phone = (c.get("phone") or "").strip()
        mobile = (c.get("mobile") or "").strip()
        if email:
            seen_email.setdefault(email, []).append(c)
        if phone:
            seen_phone.setdefault(phone, []).append(c)
        if mobile and mobile != phone:
            seen_phone.setdefault(mobile, []).append(c)

    duplicates: list[dict] = []
    for email, group in seen_email.items():
        if len(group) > 1:
            duplicates.append({"field": "email", "value": email, "customers": group})
    for phone, group in seen_phone.items():
        if len(group) > 1:
            duplicates.append({"field": "phone", "value": phone, "customers": group})

    duplicates.sort(key=lambda d: -len(d["customers"]))
    # Strip sensitive fields from customer data in duplicate groups
    for dup in duplicates:
        dup["customers"] = [_safe_customer(c) for c in dup["customers"]]
    return {"duplicates": duplicates, "count": len(duplicates)}
