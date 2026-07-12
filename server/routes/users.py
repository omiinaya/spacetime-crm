"""User routes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends

from helpers import (

    _call,
    _log_audit,
    _paginated,
    _sql,
    require_role,
)
from rate_limit import limiter

if TYPE_CHECKING:
    from models import UserCreate, UserSettingsUpdate

router = APIRouter()


@router.get("/api/users")
async def list_users(
    offset: int = 0, limit: int = 50, user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """List users with pagination."""
    rows, total = await _paginated(
        "",
        "user",
        offset=offset,
        limit=limit,
        order_by="name",
        order_desc=False,
    )
    return {"users": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/api/users")
@limiter.limit("100/minute")
async def create_user(body: UserCreate, user: Annotated[dict, Depends(require_role("admin"))]):
    await _call(
        "create_user",
        [
            body.name,
            body.email,
            body.role,
        ],
    )
    await _log_audit(user, "create", "user", body.email, f"role={body.role}")
    return {"ok": True}


@router.get("/api/users/settings")
async def get_user_settings(user: Annotated[dict, Depends(require_role("admin", "tech", "front_desk"))]):
    """Get the current user's settings (theme, default_ticket_status)."""
    rows = await _sql("SELECT * FROM user_settings WHERE user_id = {}", [user["id"]])
    if not rows:
        return {"settings": None}
    return {"settings": rows[0]}


@router.put("/api/users/settings")
@limiter.limit("100/minute")
async def update_user_settings(
    body: UserSettingsUpdate, user: Annotated[dict, Depends(require_role("admin", "tech", "front_desk"))],
):
    """Upsert the current user's settings."""
    await _call(
        "upsert_user_settings",
        [
            user["id"],
            body.theme,
            body.default_ticket_status,
        ],
    )
    await _log_audit(
        user,
        "update",
        "user_settings",
        user["id"],
        f"theme={body.theme}, default_ticket_status={body.default_ticket_status}",
    )
    return {"ok": True}
