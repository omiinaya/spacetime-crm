"""Recurring invoice routes."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends
from helpers import (
    _call,
    _fire_webhook,
    _log_audit,
    _sort,
    _sql,
    _sqlesc,
    require_role,
)
from models import RecurringInvoiceRuleCreate, RecurringInvoiceRuleUpdate

router = APIRouter()


@router.get("/api/recurring-invoices")
async def list_recurring_rules(user: dict = Depends(require_role("admin", "tech"))):
    """List all recurring invoice rules for the tenant."""
    rows = await _sql(
        f"SELECT * FROM recurring_invoice_rules WHERE tenant_id = '{_sqlesc(user['tenant_id'])}'"
    )
    # Enrich with customer name
    result = _sort(rows, "created_at", desc=True)
    for r in result:
        cust = await _sql(
            f"SELECT first_name, last_name FROM customer WHERE id = '{r.get('customer_id', '')}'"
        )
        if cust:
            c = cust[0]
            r["customer_name"] = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
        else:
            r["customer_name"] = "—"
    return {"rules": result}


@router.post("/api/recurring-invoices")
async def create_recurring_rule(
    body: RecurringInvoiceRuleCreate,
    user: dict = Depends(require_role("admin", "tech")),
):
    """Create a recurring invoice rule."""
    line_items_json = json.dumps([li.model_dump() for li in body.line_items])
    await _call(
        "create_recurring_invoice_rule",
        [
            user["tenant_id"],
            body.customer_id,
            body.name,
            body.frequency,
            body.interval_count,
            body.due_date_days,
            line_items_json,
            body.next_generation_date,
        ],
    )
    await _log_audit(user, "create", "recurring_invoice_rule", body.name)
    asyncio.ensure_future(
        _fire_webhook(
            "recurring_invoice_rule.created",
            {
                "entity_type": "recurring_invoice_rule",
                "name": body.name,
                "customer_id": body.customer_id,
                "frequency": body.frequency,
            },
        )
    )
    return {"ok": True}


@router.put("/api/recurring-invoices/{rule_id}")
async def update_recurring_rule(
    rule_id: str,
    body: RecurringInvoiceRuleUpdate,
    user: dict = Depends(require_role("admin", "tech")),
):
    """Update a recurring invoice rule."""
    line_items_json = json.dumps([li.model_dump() for li in body.line_items])
    await _call(
        "update_recurring_invoice_rule",
        [
            rule_id,
            body.name,
            body.frequency,
            body.interval_count,
            body.due_date_days,
            line_items_json,
            body.next_generation_date,
            body.status,
        ],
    )
    await _log_audit(user, "update", "recurring_invoice_rule", rule_id)
    return {"ok": True}


@router.delete("/api/recurring-invoices/{rule_id}")
async def delete_recurring_rule(
    rule_id: str,
    user: dict = Depends(require_role("admin")),
):
    """Delete a recurring invoice rule."""
    await _call("delete_recurring_invoice_rule", [rule_id])
    await _log_audit(user, "delete", "recurring_invoice_rule", rule_id)
    return {"ok": True}


@router.post("/api/recurring-invoices/generate")
async def generate_recurring_invoices(
    user: dict = Depends(require_role("admin", "tech")),
):
    """Trigger generation of due recurring invoices."""
    await _call("generate_recurring_invoices", [])
    await _log_audit(user, "generate", "recurring_invoices", "manual trigger")
    return {"ok": True}
