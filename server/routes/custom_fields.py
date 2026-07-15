"""Custom Fields routes."""

from __future__ import annotations

import json
import secrets
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends

from helpers import (
    _call,
    _log_audit,
    _paginated,
    _safe_id,
    _sql,
    require_role,
)
from rate_limit import limiter

from models.custom_fields import CustomFieldDefinitionCreate, CustomFieldValuesUpdate

router = APIRouter()


@router.get("/api/custom-field-definitions")
async def list_custom_field_definitions(
    offset: int = 0,
    limit: int = 50,
    user: dict = Depends(require_role("admin", "tech", "front_desk")),
):
    """List custom field definitions with pagination."""
    rows, total = await _paginated(
        user["tenant_id"],
        "custom_field_definitions",
        offset=offset,
        limit=limit,
        order_by="name",
        order_desc=False,
    )
    return {"custom_fields": rows, "total": total, "offset": offset, "limit": limit}


@router.post("/api/custom-field-definitions")
@limiter.limit("100/minute")
async def create_custom_field_definition(
    body: CustomFieldDefinitionCreate,
    user: Annotated[dict, Depends(require_role("admin"))],
):
    """Create a custom field definition."""
    field_id = secrets.token_hex(12)
    await _call(
        "create_custom_field_definition",
        [
            user["tenant_id"],
            field_id,
            body.entity_type,
            body.label,
            body.field_type,
            json.dumps(body.options),
            body.sort_order,
            body.required,
            body.active,
        ],
    )
    await _log_audit(user, "create", "custom_field", body.label)
    return {"ok": True, "id": field_id}


@router.put("/api/custom-field-definitions/{field_id}")
@limiter.limit("100/minute")
async def update_custom_field_definition(
    field_id: str,
    body: CustomFieldDefinitionCreate,
    user: Annotated[dict, Depends(require_role("admin"))],
):
    """Update a custom field definition."""
    await _call(
        "update_custom_field_definition",
        [
            field_id,
            body.label,
            body.field_type,
            json.dumps(body.options),
            body.sort_order,
            body.required,
            body.active,
        ],
    )
    await _log_audit(user, "update", "custom_field_definition", field_id, body.label)
    return {"ok": True}


@router.delete("/api/custom-field-definitions/{field_id}")
@limiter.limit("100/minute")
async def delete_custom_field_definition(field_id: str, user: Annotated[dict, Depends(require_role("admin"))]):
    """Delete a custom field definition."""
    await _call("delete_custom_field_definition", [field_id])
    await _log_audit(user, "delete", "custom_field_definition", field_id)
    return {"ok": True}


@router.get("/api/custom-field-values/{entity_id}")
async def get_custom_field_values(
    entity_id: str, user: Annotated[dict, Depends(require_role("admin", "tech", "front_desk"))]
):
    """Get all custom field values for an entity."""
    rows = await _sql(f"SELECT * FROM custom_field_values WHERE entity_id = '{_safe_id(entity_id)}'")
    return {"values": rows}


@router.put("/api/custom-field-values/{entity_id}")
@limiter.limit("100/minute")
async def set_custom_field_values(
    entity_id: str,
    body: CustomFieldValuesUpdate,
    user: Annotated[dict, Depends(require_role("admin", "tech", "front_desk"))],
):
    """Set custom field values for an entity. Body: { values: { field_id: value, ... } }."""
    values = body.values
    for field_id, value in values.items():
        await _call("set_custom_field_value", [entity_id, field_id, str(value), user.get("tenant_id", "")])
    return {"ok": True}
