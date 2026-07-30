"""Checklist Template routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from helpers import (
    _call,
    _log_audit,
    _paginated,
    require_role,
)
from models import ChecklistTemplateCreate, ChecklistTemplateUpdate

router = APIRouter()


@router.get("/api/checklist-templates")
async def list_checklist_templates(
    offset: int = 0,
    limit: int = 50,
    user: dict = Depends(require_role("admin", "tech")),
):
    """List all checklist templates with pagination."""
    rows, total = await _paginated(
        user["tenant_id"],
        "checklist_templates",
        offset=offset,
        limit=limit,
        order_by="name",
        order_desc=False,
    )
    return {"templates": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/api/checklist-templates")
async def create_checklist_template(
    body: ChecklistTemplateCreate, user: dict = Depends(require_role("admin"))
):
    """Create a checklist template. Items: [{\"label\":\"...\",\"order\":1}]"""
    await _call(
        "create_checklist_template",
        [
            user["tenant_id"],
            body.name,
            body.description,
            json.dumps(body.items),
        ],
    )
    await _log_audit(user, "create", "checklist_template", body.name)
    return {"ok": True}


@router.put("/api/checklist-templates/{template_id}")
async def update_checklist_template(
    template_id: str,
    body: ChecklistTemplateUpdate,
    user: dict = Depends(require_role("admin")),
):
    """Update a checklist template."""
    await _call(
        "update_checklist_template",
        [
            template_id,
            body.name,
            body.description,
            json.dumps(body.items),
        ],
    )
    await _log_audit(user, "update", "checklist_template", template_id)
    return {"ok": True}


@router.delete("/api/checklist-templates/{template_id}")
async def delete_checklist_template(template_id: str, user: dict = Depends(require_role("admin"))):
    """Delete a checklist template."""
    await _call("delete_checklist_template", [template_id])
    await _log_audit(user, "delete", "checklist_template", template_id)
    return {"ok": True}
