"""Tenant routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from helpers import (
    _call,
    _log_audit,
    _paginated,
    _safe_id,
    _sql,
    logger,
    require_role,
)
from models import (
    TenantCreate,
    TenantMemberAdd,
    TenantMemberRoleUpdate,
    TenantMigrate,
    TenantUpdate,
)

router = APIRouter()


@router.get("/api/tenants")
async def list_tenants(
    offset: int = 0, limit: int = 50, user: dict = Depends(require_role("admin"))
):
    """List all tenants with pagination."""
    try:
        rows, total = await _paginated("", "tenants", offset=offset, limit=limit, order_by="name")
        return {"tenants": rows, "total": total, "offset": offset, "limit": limit}
    except Exception as e:
        logger.warning("Failed to list tenants: %s", e)
        return {"tenants": []}


@router.post("/api/tenants")
async def create_tenant(body: TenantCreate, user: dict = Depends(require_role("admin"))):
    """Create a new tenant."""
    name = body.name.strip()
    slug = body.slug.strip()
    if not name:
        raise HTTPException(400, "name is required")
    if not slug:
        slug = name.lower().replace(" ", "-").replace("[^a-z0-9-]", "")
    await _call("create_tenant", [name, slug])
    await _log_audit(user, "create", "tenant", name, f"slug={slug}")
    return {"ok": True}


@router.get("/api/tenants/{tenant_id}")
async def get_tenant(tenant_id: str, user: dict = Depends(require_role("admin"))):
    """Get single tenant with member info."""
    _safe_id(tenant_id)
    rows = await _sql(f"SELECT * FROM tenants WHERE id = '{tenant_id}'")
    if not rows:
        raise HTTPException(404, "Tenant not found")
    tenant = rows[0]
    members = await _sql(f"SELECT * FROM tenant_members WHERE tenant_id = '{tenant_id}'")
    tenant["members"] = members
    return {"tenant": tenant}


@router.put("/api/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: str, body: TenantUpdate, user: dict = Depends(require_role("admin"))
):
    """Update tenant settings."""
    name = body.name
    slug = body.slug.strip()
    if not slug:
        slug = name.lower().replace(" ", "-").replace("[^a-z0-9-]", "")
    logo_url = body.logo_url
    settings = body.settings
    await _call("update_tenant", [tenant_id, name, slug, logo_url, settings])
    await _log_audit(user, "update", "tenant", name)
    return {"ok": True}


@router.delete("/api/tenants/{tenant_id}")
async def delete_tenant(tenant_id: str, user: dict = Depends(require_role("admin"))):
    """Delete a tenant and all its data."""
    await _call("delete_tenant", [tenant_id])
    await _log_audit(user, "delete", "tenant", tenant_id)
    return {"ok": True}


@router.post("/api/tenants/{tenant_id}/members")
async def add_tenant_member(
    tenant_id: str, body: TenantMemberAdd, user: dict = Depends(require_role("admin"))
):
    """Add a member to a tenant."""
    username = body.username.strip()
    role = body.role.strip()
    if not username:
        raise HTTPException(400, "username is required")
    await _call("add_tenant_member", [tenant_id, username, role])
    await _log_audit(user, "add_member", "tenant_member", username, f"tenant={tenant_id}")
    return {"ok": True}


@router.delete("/api/tenants/{tenant_id}/members/{member_id}")
async def remove_tenant_member(
    tenant_id: str, member_id: str, user: dict = Depends(require_role("admin"))
):
    """Remove a member from a tenant."""
    await _call("remove_tenant_member", [member_id])
    await _log_audit(user, "remove_member", "tenant_member", member_id)
    return {"ok": True}


@router.put("/api/tenants/{tenant_id}/members/{member_id}")
async def update_tenant_member_role(
    tenant_id: str,
    member_id: str,
    body: TenantMemberRoleUpdate,
    user: dict = Depends(require_role("admin")),
):
    """Update member role within a tenant."""
    role = body.role.strip()
    await _call("update_tenant_member_role", [member_id, role])
    await _log_audit(user, "update_member", "tenant_member", member_id, f"role={role}")
    return {"ok": True}


@router.post("/api/tenants/migrate")
async def migrate_to_tenant(body: TenantMigrate, user: dict = Depends(require_role("admin"))):
    """One-time migration: create a default tenant and assign all existing users to it."""
    existing = await _sql("SELECT * FROM tenants")
    if existing:
        raise HTTPException(400, "Migration already completed - tenants exist")
    name = body.name.strip()
    slug = body.slug.strip()
    if not slug:
        slug = name.lower().replace(" ", "-").replace("[^a-z0-9-]", "")
    _safe_id(slug)
    await _call("create_tenant", [name, slug])
    rows = await _sql(f"SELECT * FROM tenants WHERE slug = '{slug}'")
    if not rows:
        raise HTTPException(500, "Failed to find created tenant")
    tid = rows[0]["id"]
    users = await _sql("SELECT * FROM user")
    count = 0
    for u in users:
        await _call(
            "add_tenant_member",
            [tid, u["name"], "admin" if u.get("role") == "admin" else "user"],
        )
        count += 1
    tables = [
        "customer",
        "ticket",
        "ticket_note",
        "ticket_timer",
        "invoices",
        "invoice_line_items",
        "estimates",
        "estimate_line_items",
        "payment",
        "appointment",
        "products",
        "purchase_order",
        "purchase_order_line_item",
        "inventory_adjustment",
        "tax_rates",
        "audit_log",
        "custom_field_definitions",
        "customer_geolocations",
        "checklist_templates",
        "ticket_checklist_items",
        "webhook_subscriptions",
    ]
    updated = {}
    for tbl in tables:
        try:
            await _sql(f"UPDATE {tbl} SET tenant_id = '{tid}' WHERE tenant_id = ''")
            updated[tbl] = True
        except Exception as e:
            logger.warning("Migration update failed for %s: %s", tbl, e)
            updated[tbl] = False
    await _log_audit(user, "migrate", "tenant", name, f"users={count}")
    return {
        "ok": True,
        "tenant_id": tid,
        "users_migrated": count,
        "tables_updated": updated,
    }
