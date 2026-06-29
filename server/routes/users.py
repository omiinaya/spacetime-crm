"""User routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from helpers import (
    _sql, _paginated, _call, _log_audit,
    require_role, logger,
)
from models import UserCreate, UserUpdate

router = APIRouter()


@router.get("/api/users")
async def list_users(offset: int = 0, limit: int = 50, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """List users with pagination."""
    rows, total = await _paginated(
        "", "user",
        offset=offset, limit=limit,
        order_by="name", order_desc=False,
    )
    return {"users": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/api/users")
async def create_user(body: UserCreate, user: dict = Depends(require_role("admin"))):
    await _call("create_user", [
        body.name,
        body.email,
        body.role,
    ])
    await _log_audit(user, "create", "user", body.email, f"role={body.role}")
    return {"ok": True}
