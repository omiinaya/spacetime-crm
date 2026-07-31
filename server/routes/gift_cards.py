"""Gift card routes — sell, redeem, list, and manage."""

from __future__ import annotations

import random
import string
import time

from fastapi import APIRouter, Depends, HTTPException
from helpers import _call, _log_audit, _paginated, _sql, _sqlesc, require_role

router = APIRouter()


def _generate_gift_code(length: int = 12) -> str:
    """Generate a random alphanumeric gift card code."""
    chars = string.ascii_uppercase + string.digits
    return "GC-" + "".join(random.choices(chars, k=length))


@router.get("/api/gift-cards")
async def list_gift_cards(
    offset: int = 0,
    limit: int = 50,
    active: str = "",
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """List gift cards with optional active/inactive filter."""
    where = ""
    if active == "true":
        where = "active = true"
    elif active == "false":
        where = "active = false"
    rows, total = await _paginated(
        user["tenant_id"],
        "gift_cards",
        offset=offset,
        limit=limit,
        where_extra=where,
        order_by="created_at",
        order_desc=True,
    )
    return {"gift_cards": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/api/gift-cards")
async def create_gift_card(
    body: dict,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """Sell a new gift card."""
    amount = body.get("amount", 0)
    if amount <= 0:
        raise HTTPException(400, "Gift card amount must be positive")

    customer_id = body.get("customer_id", "")
    customer_name = body.get("customer_name", "")
    if not customer_name:
        # Look up customer name if ID is provided
        if customer_id:
            cust = await _sql(f"SELECT * FROM customer WHERE id = '{_sqlesc(customer_id)}'")
            if cust:
                customer_name = (
                    f"{cust[0].get('first_name', '')} {cust[0].get('last_name', '')}".strip()
                )
        if not customer_name:
            customer_name = "Anonymous"

    code = _generate_gift_code()
    expires_at = body.get("expires_at", 0)
    notes = body.get("notes", "")

    await _call(
        "create_gift_card",
        [
            code,
            user["tenant_id"],
            customer_id,
            customer_name,
            amount,
            user["id"],
            expires_at,
            notes,
        ],
    )
    await _log_audit(user, "create", "gift_card", code, f"amount={amount}")

    # Return the newly created gift card
    rows = await _sql(f"SELECT * FROM gift_cards WHERE code = '{_sqlesc(code)}'")
    gift = rows[0] if rows else None
    return {"ok": True, "gift_card": gift}


@router.post("/api/gift-cards/redeem")
async def redeem_gift_card(
    body: dict,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """Redeem a gift card code and deduct from balance."""
    code = body.get("code", "").strip().upper()
    amount = body.get("amount", 0)
    if not code:
        raise HTTPException(400, "Missing gift card code")
    if amount <= 0:
        raise HTTPException(400, "Redemption amount must be positive")

    rows = await _sql(
        f"SELECT * FROM gift_cards WHERE code = '{_sqlesc(code)}' AND tenant_id = '{_sqlesc(user['tenant_id'])}'"
    )
    if not rows:
        raise HTTPException(404, "Gift card not found")
    card = rows[0]
    if not card.get("active", True):
        raise HTTPException(400, "Gift card is no longer active")
    if card.get("expires_at", 0) > 0 and card["expires_at"] < int(time.time() * 1000):
        raise HTTPException(400, "Gift card has expired")
    if card["remaining_balance"] < amount:
        raise HTTPException(
            400, f"Insufficient balance: ${card['remaining_balance']:.2f} remaining"
        )

    try:
        await _call("redeem_gift_card", [card["id"], amount])
    except HTTPException as e:
        # Reducer-level validation failed (e.g. race condition drained balance).
        if e.status_code == 502:
            raise HTTPException(400, "Insufficient balance: card was already redeemed") from e
        raise
    await _log_audit(
        user,
        "redeem",
        "gift_card",
        code,
        f"amount={amount:.2f} remaining={card['remaining_balance'] - amount:.2f}",
    )
    return {"ok": True, "redeemed": amount, "remaining": card["remaining_balance"] - amount}


@router.get("/api/gift-cards/lookup")
async def lookup_gift_card(
    code: str = "",
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """Look up a gift card by code to check balance."""
    if not code:
        raise HTTPException(400, "Missing gift card code")
    code = code.strip().upper()
    rows = await _sql(
        f"SELECT * FROM gift_cards WHERE code = '{_sqlesc(code)}' AND tenant_id = '{_sqlesc(user['tenant_id'])}'"
    )
    if not rows:
        raise HTTPException(404, "Gift card not found")
    card = rows[0]
    return {"gift_card": card}


@router.post("/api/gift-cards/{gift_id}/void")
async def void_gift_card(
    gift_id: str,
    user: dict = Depends(require_role("admin")),
):
    """Void (deactivate) a gift card. Admin only, scoped to tenant."""
    rows = await _sql(
        f"SELECT * FROM gift_cards WHERE id = '{_sqlesc(gift_id)}' AND tenant_id = '{_sqlesc(user['tenant_id'])}'"
    )
    if not rows:
        raise HTTPException(404, "Gift card not found")
    card = rows[0]
    if not card.get("active", True):
        raise HTTPException(400, "Gift card is already voided")
    await _call("void_gift_card", [gift_id])
    await _log_audit(user, "void", "gift_card", gift_id, card.get("code", ""))
    return {"ok": True}
