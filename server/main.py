import json
import logging
from typing import Any
from pathlib import Path
from datetime import datetime, timedelta
import asyncio
import secrets
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from config import settings
from models import (
    LoginRequest, SetPasswordRequest,
    CustomerCreate, CustomerUpdate,
    TicketCreate, TicketStatusUpdate, TicketAssign, TicketNoteCreate, TicketTimerStart,
    InvoiceCreate, InvoiceStatusUpdate, InvoiceLineItemCreate, InvoiceTaxRateUpdate,
    PaymentCreate,
    AppointmentCreate, AppointmentStatusUpdate,
    ProductCreate, ProductQuantityUpdate,
    PurchaseOrderCreate, PurchaseOrderStatusUpdate, POLineItemCreate, POReceiveItem,
    EstimateCreate, EstimateStatusUpdate, EstimateLineItemCreate,
    TaxRateCreate, TaxRateUpdate,
    InventoryAdjustmentCreate,
    TenantCreate, TenantUpdate, TenantMemberAdd, TenantMemberRoleUpdate, TenantMigrate,
    CustomFieldDefinitionCreate, CustomFieldValuesUpdate,
    ChecklistTemplateCreate, ChecklistTemplateUpdate, ChecklistApply, ChecklistToggle,
    WebhookSubscriptionCreate, WebhookSubscriptionUpdate,
    UserCreate, UserUpdate,
    MailSettingsUpdate, SMSSettingsUpdate,
    PortalLoginRequest, PortalNoteCreate, PortalPaymentCreate, PortalSetPassword, PortalCheckoutSessionCreate,
)
from mail import get_settings as get_mail_settings, update_settings as update_mail_settings, test_connection as test_mail_connection
from mail import _notify_ticket_status_change, _notify_invoice_created, _notify_appointment_created, _notify_payment_received
from mail import _customer_email as _mail_customer_email
from sms import (
    get_settings as get_sms_settings,
    update_settings as update_sms_settings,
    test_connection as test_sms_connection,
    is_configured as sms_configured,
    send_sms as _sms_send,
    _customer_phone as _sms_customer_phone,
    _notify_ticket_status_change as _sms_ticket_status,
    _notify_invoice_created as _sms_invoice_created,
    _notify_payment_received as _sms_payment_received,
    _notify_appointment_created as _sms_appointment_created,
    _notify_estimate_approved as _sms_estimate_approved,
)
from stripe_payments import create_checkout_session, verify_webhook, is_configured as stripe_configured
from webhooks import fire_event as _fire_webhook_event, ALL_EVENTS as WEBHOOK_EVENTS
import csv
import io
import bcrypt
import jwt
from datetime import datetime, timedelta
import secrets
from fastapi import Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Generate a default JWT secret on startup if none configured
if settings.jwt_secret == "change-me-to-a-random-secret":
    settings.jwt_secret = secrets.token_hex(32)

security = HTTPBearer(auto_error=False)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SpacetimeCRM")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── STDB helpers ──────────────────────────────────────────────

async def _sql(query: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            settings.stdb_sql_url,
            content=query,
            headers={"Content-Type": "application/sql"},
        )
    if resp.status_code >= 400:
        logger.error("STDB SQL error: %s | query: %.200s", resp.text, query)
        raise HTTPException(502, f"SQL query failed: {resp.text[:200]}")
    data = resp.json()
    result: list[dict[str, Any]] = []
    if isinstance(data, list):
        for table_result in data:
            rows = table_result.get("rows", [])
            schema = table_result.get("schema", {})
            cols = [
                e["name"]["some"]
                for e in schema.get("elements", [])
                if "some" in e.get("name", {})
            ]
            for row in rows:
                result.append(dict(zip(cols, row)))
    return result


async def _sql_t(query: str, tenant_id: str) -> list[dict[str, Any]]:
    """Run a SELECT query with tenant_id filter automatically appended.
    Adds `AND tenant_id = '{tid}'` before any LIMIT clause, or at the end of the query.
    Validates tenant_id format to prevent SQL injection.
    """
    if not tenant_id:
        return await _sql(query)
    # Validate tenant_id is safe — alphanumeric, underscores, hyphens only
    if not tenant_id.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "Invalid tenant_id format")
    lowered = query.lower()
    if "where" in lowered:
        for marker in (" order by", " limit", " group by", " having"):
            idx = lowered.find(marker)
            if idx != -1:
                query = query[:idx] + f" AND tenant_id = '{tenant_id}'" + query[idx:]
                return await _sql(query)
        query += f" AND tenant_id = '{tenant_id}'"
    else:
        query = query.rstrip(";")
        lowered = query.lower()
        for marker in (" order by", " limit", " group by", " having"):
            idx = lowered.find(marker)
            if idx != -1:
                query = query[:idx] + f" WHERE tenant_id = '{tenant_id}'" + query[idx:]
                return await _sql(query)
        query += f" WHERE tenant_id = '{tenant_id}'"
    return await _sql(query)



async def _call(reducer: str, args: list[Any] | None = None) -> Any:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.stdb_call_url}/{reducer}",
            json=args or [],
        )
    if resp.status_code >= 400:
        logger.error("STDB call error (%s): %s", reducer, resp.text[:200])
        raise HTTPException(502, f"Reducer call failed: {resp.text[:200]}")
    try:
        return resp.json()
    except Exception:
        return {"ok": True}


def _sort(rows: list[dict], key: str, desc: bool = True) -> list[dict]:
    """Sort rows by key, handling mixed types without crashing."""
    def sort_key(r):
        val = r.get(key)
        if val is None:
            return ("", 0) if desc else ("zzzz", 999999)
        return (str(val), val)
    return sorted(rows, key=sort_key, reverse=desc)


async def _log_audit(user: dict, action: str, entity: str, entity_id: str, details: str = ""):
    """Record an audit log entry. Fire-and-forget — never raises."""
    try:
        await _call("log_audit", [
            user.get("tenant_id", ""),
            user.get("id", ""),
            user.get("name", ""),
            action,
            entity,
            entity_id,
            details,
        ])
    except Exception as e:
        logger.warning("Audit log failed: %s", e)


# ── Webhook helper ─────────────────────────────────────────────


async def _get_webhook_subscriptions() -> list[dict[str, Any]]:
    """Fetch all webhook subscriptions from STDB."""
    try:
        return await _sql("SELECT * FROM webhook_subscriptions")
    except Exception:
        return []


async def _fire_webhook(event_type: str, payload: dict[str, Any]) -> None:
    """Fire a webhook event to all matching subscriptions. Never raises."""
    try:
        subs = await _get_webhook_subscriptions()
        if subs:
            await _fire_webhook_event(event_type, payload, subs)
    except Exception as e:
        logger.warning("Webhook fire failed (%s): %s", event_type, e)


# ── Jinja2 template loader ────────────────────────────────────

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

STATUS_LABELS = {
    "draft": "Draft", "sent": "Sent", "paid": "Paid",
    "partial": "Partial", "overdue": "Overdue", "cancelled": "Cancelled",
}

STATUS_CSS = {
    "draft": "draft", "sent": "sent", "paid": "paid",
    "partial": "partial", "overdue": "overdue", "cancelled": "cancelled",
}


# ── Role-based permissions ─────────────────────────────────────


def require_role(*roles: str):
    """FastAPI dependency: validate JWT and check role membership."""
    async def _check(credentials: HTTPAuthorizationCredentials = Depends(security)):
        if credentials is None:
            raise HTTPException(401, "Not authenticated")
        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid token")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token: no subject")
        rows = await _sql(f"SELECT * FROM user WHERE id = '{user_id}'")
        if not rows:
            raise HTTPException(401, "User not found")
        user = rows[0]
        user["tenant_id"] = payload.get("tenant_id", "")
        if not user.get("active", False):
            raise HTTPException(403, "User account is disabled")
        if user.get("role") not in roles:
            raise HTTPException(
                403,
                f"Access denied. Requires one of roles: {', '.join(roles)}. "
                f"Your role: {user.get('role', 'unknown')}",
            )
        return user
    return _check


# ── CUSTOMER endpoints ────────────────────────────────────────

@app.get("/api/customers")
async def list_customers(search: str = "", user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql_t("SELECT * FROM customer", user["tenant_id"])
    q = search.lower().strip()
    if q:
        rows = [
            r for r in rows
            if q in (r.get("first_name") or "").lower()
            or q in (r.get("last_name") or "").lower()
            or q in (r.get("email") or "").lower()
            or q in (r.get("phone") or "")
        ]
    return {"customers": _sort(rows, "created_at")}


@app.post("/api/customers")
async def create_customer(body: CustomerCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("create_customer", [
        user["tenant_id"],
        body.first_name,
        body.last_name,
        body.email,
        body.phone,
    ])
    details = f"{body.first_name} {body.last_name}".strip()
    await _log_audit(user, "create", "customer", details, f"email={body.email}")
    asyncio.ensure_future(_fire_webhook("customer.created", {
        "entity_type": "customer",
        "name": details,
        "email": body.email,
    }))
    return {"ok": True}


@app.put("/api/customers/{customer_id}")
async def update_customer(customer_id: str, body: CustomerUpdate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("update_customer", [
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
    ])
    await _log_audit(user, "update", "customer", customer_id)
    asyncio.ensure_future(_fire_webhook("customer.updated", {
        "entity_type": "customer",
        "id": customer_id,
    }))
    return {"ok": True}


@app.delete("/api/customers/{customer_id}")
async def delete_customer(customer_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_customer", [customer_id])
    await _log_audit(user, "delete", "customer", customer_id)
    asyncio.ensure_future(_fire_webhook("customer.deleted", {
        "entity_type": "customer",
        "id": customer_id,
    }))
    return {"ok": True}


@app.post("/api/customers/{customer_id}/portal-password")
async def set_customer_portal_password(customer_id: str, body: SetPasswordRequest, user: dict = Depends(require_role("admin"))):
    """Admin sets/resets a customer's portal password."""
    pw = body.password
    if len(pw) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    await _call("set_customer_password", [customer_id, hashed])
    await _log_audit(user, "update", "customer_portal_password", customer_id)
    return {"ok": True}


# ── CUSTOMER GEOLOCATION endpoints ─────────────────────────────

@app.get("/api/customers/geolocations")
async def list_customer_geolocations(user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """Return all customers with their geolocation data for the map."""
    customers = await _sql_t("SELECT * FROM customer", user["tenant_id"])
    geos = await _sql_t("SELECT * FROM customer_geolocations", user["tenant_id"])
    geo_map = {g["customer_id"]: g for g in geos}
    result = []
    for c in customers:
        loc = geo_map.get(c["id"])
        full_name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
        addr_parts = [c.get("address_line1", ""), c.get("city", ""), c.get("state", ""), c.get("zip", "")]
        address = ", ".join(a for a in addr_parts if a)
        result.append({
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
        })
    return {"locations": result}


@app.post("/api/customers/{customer_id}/geocode")
async def geocode_customer(customer_id: str, user: dict = Depends(require_role("admin", "tech"))):
    """Geocode a single customer's address and store the location."""
    customers = await _sql(f"SELECT * FROM customer WHERE id = '{customer_id}'")
    if not customers:
        raise HTTPException(404, "Customer not found")
    c = customers[0]
    addr_parts = [c.get("address_line1", ""), c.get("city", ""), c.get("state", ""), c.get("zip", "")]
    address = ", ".join(a for a in addr_parts if a)
    if not address:
        raise HTTPException(400, "Customer has no address to geocode")

    # Use Nominatim (OpenStreetMap free geocoding API)
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "SpacetimeCRM/1.0"},
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


@app.post("/api/customers/geocode-all")
async def geocode_all_customers(user: dict = Depends(require_role("admin"))):
    """Geocode all customers without stored locations."""
    customers = await _sql_t("SELECT * FROM customer", user["tenant_id"])
    geos = await _sql_t("SELECT * FROM customer_geolocations", user["tenant_id"])
    geo_ids = {g["customer_id"] for g in geos}

    results = []
    for c in customers:
        if c["id"] in geo_ids:
            continue
        addr_parts = [c.get("address_line1", ""), c.get("city", ""), c.get("state", ""), c.get("zip", "")]
        address = ", ".join(a for a in addr_parts if a)
        if not address:
            continue
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": address, "format": "json", "limit": 1},
                    headers={"User-Agent": "SpacetimeCRM/1.0"},
                )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    lat = float(data[0]["lat"])
                    lng = float(data[0]["lon"])
                    await _call("set_customer_geolocation", [user["tenant_id"], c["id"], lat, lng])
                    results.append({"id": c["id"], "name": f"{c['first_name']} {c['last_name']}".strip(), "latitude": lat, "longitude": lng, "status": "geocoded"})
                else:
                    results.append({"id": c["id"], "name": f"{c['first_name']} {c['last_name']}".strip(), "status": "not_found"})
            else:
                results.append({"id": c["id"], "name": f"{c['first_name']} {c['last_name']}".strip(), "status": "error"})
        except Exception as e:
            results.append({"id": c["id"], "name": f"{c['first_name']} {c['last_name']}".strip(), "status": f"error: {str(e)[:50]}"})

    return {"geocoded": len([r for r in results if r.get("latitude")]), "results": results}


# ── TICKET endpoints ──────────────────────────────────────────

@app.get("/api/tickets")
async def list_tickets(status: str = "", user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql_t("SELECT * FROM ticket", user["tenant_id"])
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return {"tickets": _sort(rows, "created_at")}


@app.post("/api/tickets")
async def create_ticket(body: TicketCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("create_ticket", [
        user["tenant_id"],
        body.customer_id,
        body.title,
        body.description,
        body.device_type,
        body.device_model,
        body.device_serial,
        body.priority,
    ])
    await _log_audit(user, "create", "ticket", body.title, f"customer={body.customer_id}")
    asyncio.ensure_future(_fire_webhook("ticket.created", {
        "entity_type": "ticket",
        "title": body.title,
        "customer_id": body.customer_id,
    }))
    return {"ok": True}


@app.put("/api/tickets/{ticket_id}/status")
async def update_ticket_status(ticket_id: str, body: TicketStatusUpdate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    status = body.status
    await _call("update_ticket_status", [ticket_id, status])

    # Notification: ticket status changed
    async def _notify():
        rows = await _sql(f"SELECT * FROM ticket WHERE id = '{ticket_id}'")
        if rows:
            t = rows[0]
            cust = await _sql(f"SELECT * FROM customer WHERE id = '{t.get('customer_id', '')}'")
            email = _mail_customer_email(cust[0]) if cust else None
            if email:
                link = f"http://localhost:{settings.server_port}/portal/"
                _notify_ticket_status_change(email, t.get("ticket_number", 0), t.get("title", ""), status, link)
            phone = _sms_customer_phone(cust[0]) if cust else None
            if phone:
                _sms_ticket_status(phone, t.get("ticket_number", 0), t.get("title", ""), status)
    asyncio.ensure_future(_notify())

    # Fire webhook
    asyncio.ensure_future(_fire_webhook("ticket.status_changed", {
        "entity_type": "ticket",
        "id": ticket_id,
        "status": status,
    }))

    return {"ok": True}


@app.put("/api/tickets/{ticket_id}/assign")
async def assign_ticket(ticket_id: str, body: TicketAssign, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("assign_ticket", [ticket_id, body.assigned_user_id])
    await _log_audit(user, "assign", "ticket", ticket_id, f"user={body.assigned_user_id}")
    return {"ok": True}


@app.get("/api/tickets/{ticket_id}/notes")
async def get_ticket_notes(ticket_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql(f"SELECT * FROM ticket_note WHERE ticket_id = '{ticket_id}'")
    return {"notes": _sort(rows, "created_at", desc=False)}


@app.post("/api/tickets/{ticket_id}/notes")
async def add_ticket_note(ticket_id: str, body: TicketNoteCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("add_ticket_note", [
        ticket_id,
        body.author or user.get("name", ""),
        body.content,
        body.internal,
    ])
    await _log_audit(user, "add_note", "ticket", ticket_id)
    return {"ok": True}


@app.delete("/api/tickets/{ticket_id}")
async def delete_ticket(ticket_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_ticket", [ticket_id])
    await _log_audit(user, "delete", "ticket", ticket_id)
    return {"ok": True}


# ── TICKET TIMER endpoints ────────────────────────────────────

@app.post("/api/tickets/{ticket_id}/timers/start")
async def start_ticket_timer(ticket_id: str, body: TicketTimerStart, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("start_ticket_timer", [ticket_id, body.user_id])
    rows = await _sql(f"SELECT * FROM ticket_timer WHERE ticket_id = '{ticket_id}'")
    return {"timers": _sort(rows, "start_time")}


@app.get("/api/timers")
async def list_all_timers(user_id: str = "", running: str = "", user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    query = "SELECT * FROM ticket_timer"
    filters = []
    if user_id:
        filters.append(f"user_id = '{user_id}'")
    if running == "true":
        filters.append("running = true")
    if filters:
        query += " WHERE " + " AND ".join(filters)
    rows = await _sql(query)
    return {"timers": _sort(rows, "start_time")}


@app.post("/api/timers/{timer_id}/stop")
async def stop_ticket_timer(timer_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("stop_ticket_timer", [timer_id])
    return {"ok": True}


@app.delete("/api/timers/{timer_id}")
async def delete_ticket_timer(timer_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_ticket_timer", [timer_id])
    return {"ok": True}


# ── INVOICE endpoints ─────────────────────────────────────────

@app.get("/api/invoices")
async def list_invoices(status: str = "", user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql_t("SELECT * FROM invoices", user["tenant_id"])
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return {"invoices": _sort(rows, "created_at")}


@app.post("/api/invoices")
async def create_invoice(body: InvoiceCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("create_invoice", [
        user["tenant_id"],
        body.customer_id,
        body.ticket_id,
        body.notes,
        body.terms,
        body.due_date,
    ])

    # Notification: invoice created
    async def _notify():
        cust = await _sql(f"SELECT * FROM customer WHERE id = '{body.customer_id}'")
        email = _mail_customer_email(cust[0]) if cust else None
        if email:
            invs = await _sql("SELECT * FROM invoices LIMIT 1")
            if invs:
                inv = invs[0]
                link = f"http://localhost:{settings.server_port}/portal/"
                _notify_invoice_created(email, inv.get("invoice_number", 0), float(inv.get("total", 0)), link)
        phone = _sms_customer_phone(cust[0]) if cust else None
        if phone:
            invs = await _sql("SELECT * FROM invoices LIMIT 1")
            if invs:
                inv = invs[0]
                _sms_invoice_created(phone, inv.get("invoice_number", 0), float(inv.get("total", 0)))
    asyncio.ensure_future(_notify())

    await _log_audit(user, "create", "invoice", f"cust={body.customer_id}")
    asyncio.ensure_future(_fire_webhook("invoice.created", {
        "entity_type": "invoice",
        "customer_id": body.customer_id,
        "ticket_id": body.ticket_id,
    }))
    return {"ok": True}


@app.put("/api/invoices/{invoice_id}/status")
async def update_invoice_status(invoice_id: str, body: InvoiceStatusUpdate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("update_invoice_status", [invoice_id, body.status])
    new_status = body.status
    await _log_audit(user, "update_status", "invoice", invoice_id, f"status={new_status}")
    asyncio.ensure_future(_fire_webhook("invoice.status_changed" if new_status != "paid" else "invoice.paid", {
        "entity_type": "invoice",
        "id": invoice_id,
        "status": new_status,
    }))
    return {"ok": True}


@app.get("/api/invoices/{invoice_id}/line-items")
async def get_invoice_line_items(invoice_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql(f"SELECT * FROM invoice_line_items WHERE invoice_id = '{invoice_id}'")
    return {"line_items": _sort(rows, "sort_order", desc=False)}


@app.post("/api/invoices/{invoice_id}/line-items")
async def add_invoice_line_item(invoice_id: str, body: InvoiceLineItemCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("add_invoice_line_item", [
        invoice_id,
        body.item_type,
        body.description,
        body.quantity,
        body.unit_price,
    ])
    await _log_audit(user, "create", "line_item", invoice_id, body.description)
    return {"ok": True}


@app.delete("/api/invoices/{invoice_id}/line-items/{item_id}")
async def delete_invoice_line_item(invoice_id: str, item_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_invoice_line_item", [item_id])
    await _log_audit(user, "delete", "line_item", invoice_id)
    return {"ok": True}


@app.delete("/api/invoices/{invoice_id}")
async def delete_invoice(invoice_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_invoice", [invoice_id])
    await _log_audit(user, "delete", "invoice", invoice_id)
    return {"ok": True}


@app.put("/api/invoices/{invoice_id}/tax-rate")
async def set_invoice_tax_rate(invoice_id: str, body: InvoiceTaxRateUpdate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("set_invoice_tax_rate", [invoice_id, body.tax_rate])
    await _log_audit(user, "update", "invoice_tax", invoice_id, f"rate={body.tax_rate}")
    return {"ok": True}


@app.get("/api/invoices/{invoice_id}/pdf")
async def invoice_pdf(invoice_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    invs = await _sql(f"SELECT * FROM invoices WHERE id = '{invoice_id}'")
    if not invs:
        raise HTTPException(404, "Invoice not found")
    inv = invs[0]
    items = await _sql(f"SELECT * FROM invoice_line_items WHERE invoice_id = '{invoice_id}'")
    items = _sort(items, "sort_order", desc=False)
    cust = await _sql(f"SELECT * FROM customer WHERE id = '{inv['customer_id']}'")

    customer = cust[0] if cust else {}
    status = inv.get("status", "draft")
    ts = inv.get("created_at", 0) / 1000
    due = inv.get("due_date", 0) / 1000

    template = jinja_env.get_template("invoice.html")
    html = template.render(
        status=STATUS_CSS.get(status, "draft"),
        status_label=STATUS_LABELS.get(status, status.capitalize()),
        invoice_number=inv.get("invoice_number", ""),
        customer_name=f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or "—",
        customer_company=customer.get("company", ""),
        customer_address=", ".join(filter(None, [
            customer.get("address_line1", ""),
            customer.get("city", ""),
            customer.get("state", ""),
        ])),
        customer_email=customer.get("email", ""),
        customer_phone=customer.get("phone", ""),
        date=datetime.fromtimestamp(ts).strftime("%b %d, %Y") if ts else "—",
        due_date=datetime.fromtimestamp(due).strftime("%b %d, %Y") if due else "—",
        terms=inv.get("terms", ""),
        notes=inv.get("notes", ""),
        subtotal=f"{float(inv.get('subtotal', 0)):.2f}",
        total=f"{float(inv.get('total', 0)):.2f}",
        tax_amount=f"{float(inv.get('tax_amount', 0)):.2f}",
        tax_rate=f"{float(inv.get('tax_rate', 0)) * 100:.1f}",
        discount_amount=float(inv.get("discount_amount", 0)),
        items=[
            {
                "description": i.get("description", ""),
                "quantity": i.get("quantity", 1),
                "unit_price": f"{float(i.get('unit_price', 0)):.2f}",
                "total": f"{float(i.get('total', 0)):.2f}",
            }
            for i in items
        ],
    )

    pdf = HTML(string=html).write_pdf()
    filename = f"invoice_{inv.get('invoice_number', 'unknown')}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# ── PAYMENT endpoints ─────────────────────────────────────────

@app.get("/api/payments")
async def list_payments(invoice_id: str = "", user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql_t("SELECT * FROM payment", user["tenant_id"])
    if invoice_id:
        rows = [r for r in rows if r.get("invoice_id") == invoice_id]
    return {"payments": _sort(rows, "created_at")}


@app.post("/api/payments")
async def record_payment(body: PaymentCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    invoice_id = body.invoice_id
    await _call("record_payment", [
        user["tenant_id"],
        invoice_id,
        body.customer_id,
        body.amount,
        body.method,
        body.reference,
        body.notes,
    ])
    # Auto-update invoice status based on total payments
    if invoice_id:
        invoices = await _sql(f"SELECT * FROM invoices WHERE id = '{invoice_id}'")
        payments = await _sql(f"SELECT * FROM payment WHERE invoice_id = '{invoice_id}'")
        if invoices:
            inv = invoices[0]
            total_paid = sum(float(p.get("amount", 0)) for p in payments)
            inv_total = float(inv.get("total", 0))
            new_status = "paid" if total_paid >= inv_total else "partial" if total_paid > 0 else inv.get("status", "draft")
            if new_status != inv.get("status"):
                await _call("update_invoice_status", [invoice_id, new_status])

            # Notification: payment received
            async def _notify():
                cust = await _sql(f"SELECT * FROM customer WHERE id = '{body.customer_id}'")
                email = _mail_customer_email(cust[0]) if cust else None
                if email:
                    link = f"http://localhost:{settings.server_port}/portal/"
                    _notify_payment_received(email, inv.get("invoice_number", 0), float(body.amount), link)
                phone = _sms_customer_phone(cust[0]) if cust else None
                if phone:
                    _sms_payment_received(phone, inv.get("invoice_number", 0), float(body.amount))
            asyncio.ensure_future(_notify())

    await _log_audit(user, "create", "payment", invoice_id, f"amount={body.amount}")
    asyncio.ensure_future(_fire_webhook("payment.created", {
        "entity_type": "payment",
        "invoice_id": invoice_id,
        "customer_id": body.customer_id,
        "amount": body.amount,
    }))
    return {"ok": True}


@app.delete("/api/payments/{payment_id}")
async def delete_payment(payment_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_payment", [payment_id])
    await _log_audit(user, "delete", "payment", payment_id)
    return {"ok": True}


# ── APPOINTMENT endpoints ─────────────────────────────────────

@app.get("/api/appointments")
async def list_appointments(user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql_t("SELECT * FROM appointment", user["tenant_id"])
    return {"appointments": _sort(rows, "start_time", desc=False)}


@app.post("/api/appointments")
async def create_appointment(body: AppointmentCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("create_appointment", [
        user["tenant_id"],
        body.customer_id,
        body.ticket_id,
        body.title,
        body.description,
        body.start_time,
        body.end_time,
        body.all_day,
    ])

    # Notification: appointment created
    async def _notify():
        cust = await _sql(f"SELECT * FROM customer WHERE id = '{body.customer_id}'")
        email = _mail_customer_email(cust[0]) if cust else None
        if email:
            link = f"http://localhost:{settings.server_port}/portal/"
            _notify_appointment_created(email, body.title, body.start_time, link)
        phone = _sms_customer_phone(cust[0]) if cust else None
        if phone:
            _sms_appointment_created(phone, body.title, body.start_time)
    asyncio.ensure_future(_notify())

    await _log_audit(user, "create", "appointment", body.title)
    asyncio.ensure_future(_fire_webhook("appointment.created", {
        "entity_type": "appointment",
        "title": body.title,
        "customer_id": body.customer_id,
        "start_time": body.start_time,
    }))
    return {"ok": True}


@app.put("/api/appointments/{appt_id}/status")
async def update_appointment_status(appt_id: str, body: AppointmentStatusUpdate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("update_appointment_status", [appt_id, body.status])
    await _log_audit(user, "update_status", "appointment", appt_id, f"status={body.status}")
    return {"ok": True}


@app.delete("/api/appointments/{appt_id}")
async def delete_appointment(appt_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_appointment", [appt_id])
    await _log_audit(user, "delete", "appointment", appt_id)
    return {"ok": True}


# ── PRODUCT endpoints ─────────────────────────────────────────

@app.get("/api/products")
async def list_products(search: str = "", user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql_t("SELECT * FROM products", user["tenant_id"])
    q = search.lower().strip()
    if q:
        rows = [
            r for r in rows
            if q in (r.get("name") or "").lower()
            or q in (r.get("sku") or "").lower()
            or q in (r.get("barcode") or "").lower()
        ]
    return {"products": _sort(rows, "name", desc=False)}


@app.post("/api/products")
async def create_product(body: ProductCreate, user: dict = Depends(require_role("admin", "tech"))):
    await _call("create_product", [
        user["tenant_id"],
        body.name,
        body.sku,
        body.barcode,
        body.description,
        body.category,
        body.price,
        body.cost,
        body.quantity_on_hand,
    ])
    await _log_audit(user, "create", "product", body.name)
    return {"ok": True}


@app.put("/api/products/{product_id}/quantity")
async def update_product_quantity(product_id: str, body: ProductQuantityUpdate, user: dict = Depends(require_role("admin", "tech"))):
    await _call("update_product_quantity", [product_id, body.quantity_on_hand])
    await _log_audit(user, "update", "product_qty", product_id, f"qty={body.quantity_on_hand}")
    return {"ok": True}


@app.delete("/api/products/{product_id}")
async def delete_product(product_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_product", [product_id])
    await _log_audit(user, "delete", "product", product_id)
    return {"ok": True}


# ── INVENTORY ADJUSTMENT endpoints ────────────────────────────

@app.get("/api/products/{product_id}/adjustments")
async def get_product_adjustments(product_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql(f"SELECT * FROM inventory_adjustment WHERE product_id = '{product_id}'")
    return {"adjustments": _sort(rows, "created_at")}


@app.post("/api/products/{product_id}/adjustments")
async def create_adjustment(product_id: str, body: InventoryAdjustmentCreate, user: dict = Depends(require_role("admin", "tech"))):
    await _call("create_inventory_adjustment", [
        user["tenant_id"],
        product_id,
        body.quantity_change,
        body.reason,
        body.reference_id,
        body.notes,
        body.user_id,
    ])
    await _log_audit(user, "create", "adjustment", product_id, f"qty={body.quantity_change}")
    return {"ok": True}


# ── TAX RATE endpoints ─────────────────────────────────────────

@app.get("/api/tax-rates")
async def list_tax_rates(user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql_t("SELECT * FROM tax_rates", user["tenant_id"])
    return {"tax_rates": _sort(rows, "name", desc=False)}


@app.post("/api/tax-rates")
async def create_tax_rate(body: TaxRateCreate, user: dict = Depends(require_role("admin"))):
    await _call("create_tax_rate", [
        user["tenant_id"],
        body.name,
        body.rate,
        body.is_default,
    ])
    await _log_audit(user, "create", "tax_rate", body.name, f"rate={body.rate}")
    return {"ok": True}


@app.put("/api/tax-rates/{tax_id}")
async def update_tax_rate(tax_id: str, body: TaxRateUpdate, user: dict = Depends(require_role("admin"))):
    await _call("update_tax_rate", [
        tax_id,
        body.name,
        body.rate,
        body.is_default,
    ])
    await _log_audit(user, "update", "tax_rate", tax_id, f"rate={body.rate}")
    return {"ok": True}


@app.delete("/api/tax-rates/{tax_id}")
async def delete_tax_rate(tax_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_tax_rate", [tax_id])
    await _log_audit(user, "delete", "tax_rate", tax_id)
    return {"ok": True}


# ── ESTIMATE endpoints ────────────────────────────────────────

@app.get("/api/estimates")
async def list_estimates(status: str = "", user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql_t("SELECT * FROM estimates", user["tenant_id"])
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return {"estimates": _sort(rows, "created_at")}


@app.post("/api/estimates")
async def create_estimate(body: EstimateCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("create_estimate", [
        user["tenant_id"],
        body.customer_id,
        body.ticket_id,
        body.notes,
        body.expires_at,
    ])
    await _log_audit(user, "create", "estimate", f"cust={body.customer_id}")
    asyncio.ensure_future(_fire_webhook("estimate.created", {
        "entity_type": "estimate",
        "customer_id": body.customer_id,
        "ticket_id": body.ticket_id,
    }))
    return {"ok": True}


@app.put("/api/estimates/{estimate_id}/status")
async def update_estimate_status(estimate_id: str, body: EstimateStatusUpdate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("update_estimate_status", [estimate_id, body.status])
    await _log_audit(user, "update_status", "estimate", estimate_id, f"status={body.status}")
    return {"ok": True}


@app.get("/api/estimates/{estimate_id}/line-items")
async def get_estimate_line_items(estimate_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql(f"SELECT * FROM estimate_line_items WHERE estimate_id = '{estimate_id}'")
    return {"line_items": _sort(rows, "sort_order", desc=False)}


@app.post("/api/estimates/{estimate_id}/line-items")
async def add_estimate_line_item(estimate_id: str, body: EstimateLineItemCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("add_estimate_line_item", [
        estimate_id,
        body.item_type,
        body.description,
        body.quantity,
        body.unit_price,
    ])
    await _log_audit(user, "create", "est_line_item", estimate_id, body.description)
    return {"ok": True}


@app.delete("/api/estimates/{estimate_id}")
async def delete_estimate(estimate_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_estimate", [estimate_id])
    await _log_audit(user, "delete", "estimate", estimate_id)
    return {"ok": True}


@app.post("/api/estimates/{estimate_id}/convert")
async def convert_estimate(estimate_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """Convert an approved estimate to an invoice (atomic reducer)."""
    est_rows = await _sql(f"SELECT * FROM estimates WHERE id = '{estimate_id}'")
    if not est_rows:
        raise HTTPException(404, "Estimate not found")
    est = est_rows[0]
    if est.get("status") != "approved":
        raise HTTPException(400, "Only approved estimates can be converted")

    # Call the atomic Rust reducer that creates invoice + copies line items
    await _call("convert_estimate_to_invoice", [estimate_id])

    # Read back the invoice_id that the reducer stored on the estimate
    est_rows = await _sql(f"SELECT invoice_id FROM estimates WHERE id = '{estimate_id}'")
    inv_id = est_rows[0].get("invoice_id", "") if est_rows else ""
    if not inv_id:
        raise HTTPException(500, "Failed to get generated invoice ID")

    await _log_audit(user, "convert", "estimate", estimate_id, f"invoice_id={inv_id}")
    
    # Fire webhook
    asyncio.ensure_future(_fire_webhook("estimate.approved", {
        "entity_type": "estimate",
        "id": estimate_id,
        "customer_id": est.get("customer_id", ""),
        "total": est.get("total", 0),
        "invoice_id": inv_id,
    }))

    # Send SMS notification for approved estimate
    async def _sms_notify():
        cust = await _sql(f"SELECT * FROM customer WHERE id = '{est.get('customer_id', '')}'")
        phone = _sms_customer_phone(cust[0]) if cust else None
        if phone:
            _sms_estimate_approved(phone, est.get("estimate_number", 0), float(est.get("total", 0)))
    asyncio.ensure_future(_sms_notify())

    return {"ok": True, "invoice_id": inv_id}


# ── PURCHASE ORDER endpoints ──────────────────────────────────

@app.get("/api/purchase-orders")
async def list_purchase_orders(user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql_t("SELECT * FROM purchase_order", user["tenant_id"])
    return {"purchase_orders": _sort(rows, "created_at")}


@app.post("/api/purchase-orders")
async def create_purchase_order(body: PurchaseOrderCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("create_purchase_order", [
        user["tenant_id"],
        body.vendor_name,
        body.notes,
    ])
    await _log_audit(user, "create", "purchase_order", body.vendor_name)
    return {"ok": True}


@app.delete("/api/purchase-orders/{po_id}")
async def delete_purchase_order(po_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_purchase_order", [po_id])
    await _log_audit(user, "delete", "purchase_order", po_id)
    return {"ok": True}


@app.get("/api/purchase-orders/{po_id}")
async def get_purchase_order(po_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql(f"SELECT * FROM purchase_order WHERE id = '{po_id}'")
    if not rows:
        raise HTTPException(404, "Purchase order not found")
    po = rows[0]
    items = await _sql(f"SELECT * FROM purchase_order_line_item WHERE purchase_order_id = '{po_id}'")
    po["line_items"] = _sort(items, "description", desc=False)
    # Calculate receipt progress
    total_qty = sum(float(i.get("quantity", 0)) for i in items)
    total_received = sum(float(i.get("received_quantity", 0)) for i in items)
    po["receipt_progress"] = round((total_received / total_qty * 100) if total_qty > 0 else 0, 1)
    return {"purchase_order": po}


@app.post("/api/purchase-orders/{po_id}/line-items")
async def add_po_line_item(po_id: str, body: POLineItemCreate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("add_po_line_item", [
        po_id,
        body.product_id,
        body.description,
        body.quantity,
        body.unit_price,
    ])
    await _log_audit(user, "create", "po_line_item", po_id, body.description)
    return {"ok": True}


@app.delete("/api/purchase-orders/{po_id}/line-items/{item_id}")
async def delete_po_line_item(po_id: str, item_id: str, user: dict = Depends(require_role("admin"))):
    await _call("delete_po_line_item", [po_id, item_id])
    await _log_audit(user, "delete", "po_line_item", po_id)
    return {"ok": True}


@app.put("/api/purchase-orders/{po_id}/status")
async def update_po_status(po_id: str, body: PurchaseOrderStatusUpdate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    await _call("update_po_status", [po_id, body.status])
    await _log_audit(user, "update_status", "purchase_order", po_id, f"status={body.status}")
    return {"ok": True}


@app.post("/api/purchase-orders/{po_id}/receive")
async def receive_po_items(po_id: str, body: POReceiveItem, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """Receive multiple items on a PO at once.
    Body: { items: [{ id: string, received_quantity: number }] }
    """
    items = body.items
    for item in items:
        await _call("receive_po_item", [item["id"], item.get("received_quantity", 0)])
    await _log_audit(user, "receive", "purchase_order", po_id, f"{len(items)} items")
    return {"ok": True}


# ── DASHBOARD stats ───────────────────────────────────────────

@app.get("/api/stats")
async def dashboard_stats(user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    all_customers = await _sql_t("SELECT * FROM customer", user["tenant_id"])
    all_tickets = await _sql_t("SELECT * FROM ticket", user["tenant_id"])
    all_invoices = await _sql_t("SELECT * FROM invoices", user["tenant_id"])
    all_appointments = await _sql_t("SELECT * FROM appointment", user["tenant_id"])
    total_customers = len(all_customers)
    total_tickets = len(all_tickets)
    open_tickets = sum(1 for t in all_tickets if t.get("status") not in ("resolved", "closed"))
    revenue = sum(float(i.get("total", 0)) for i in all_invoices if i.get("status") == "paid")
    pending_revenue = sum(float(i.get("total", 0)) for i in all_invoices if i.get("status") not in ("paid", "cancelled"))
    upcoming_appointments = sum(1 for a in all_appointments if a.get("start_time", 0) > 0)
    return {
        "total_customers": total_customers,
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "revenue": revenue,
        "pending_revenue": pending_revenue,
        "upcoming_appointments": upcoming_appointments,
    }


@app.get("/api/reports")
async def get_reports(user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """Reporting data for charts."""
    now = datetime.utcnow()

    # ── All data ──
    all_tickets = await _sql_t("SELECT * FROM ticket", user["tenant_id"])
    all_invoices = await _sql_t("SELECT * FROM invoices", user["tenant_id"])
    all_payments = await _sql_t("SELECT * FROM payment", user["tenant_id"])
    all_appointments = await _sql_t("SELECT * FROM appointment", user["tenant_id"])

    # ── Revenue by month (last 12 months) ──
    revenue_by_month = []
    for i in range(11, -1, -1):
        month_start = datetime(now.year, now.month, 1) - timedelta(days=30 * i)
        month_start_ts = int(month_start.timestamp() * 1000)
        month_end_ts = int((month_start + timedelta(days=30)).timestamp() * 1000)
        month_label = month_start.strftime("%b %y")
        month_revenue = sum(
            float(p.get("amount", 0))
            for p in all_payments
            if month_start_ts <= p.get("created_at", 0) < month_end_ts
        )
        revenue_by_month.append({"month": month_label, "revenue": round(month_revenue, 2)})

    # ── Ticket counts by status ──
    status_counts: dict[str, int] = {}
    for t in all_tickets:
        s = t.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
    ticket_by_status = [
        {"status": s, "count": c} for s, c in sorted(status_counts.items())
    ]

    # ── Invoice by status ──
    inv_status_counts: dict[str, int] = {}
    for inv in all_invoices:
        s = inv.get("status", "draft")
        inv_status_counts[s] = inv_status_counts.get(s, 0) + 1
    invoice_by_status = [
        {"status": s, "count": c} for s, c in sorted(inv_status_counts.items())
    ]

    # ── Appointments by month (next 3 + past 9) ──
    appt_by_month = []
    for i in range(11, -1, -1):
        month_start = datetime(now.year, now.month, 1) - timedelta(days=30 * i)
        month_start_ts = int(month_start.timestamp() * 1000)
        month_end_ts = int((month_start + timedelta(days=30)).timestamp() * 1000)
        month_label = month_start.strftime("%b %y")
        month_count = sum(
            1 for a in all_appointments
            if month_start_ts <= a.get("start_time", 0) < month_end_ts
        )
        appt_by_month.append({"month": month_label, "appointments": month_count})

    # ── Totals ──
    total_revenue = sum(float(p.get("amount", 0)) for p in all_payments)
    total_tickets = len(all_tickets)
    open_tickets = sum(1 for t in all_tickets if t.get("status") not in ("resolved", "closed"))
    total_sent = sum(1 for inv in all_invoices if inv.get("status") not in ("draft", "cancelled"))
    total_paid = sum(1 for inv in all_invoices if inv.get("status") == "paid")

    # ── Outstanding revenue (sent + overdue, not paid) ──
    outstanding_revenue = sum(
        float(inv.get("total", 0)) for inv in all_invoices
        if inv.get("status") in ("sent", "overdue", "partial")
    )

    # ── Average resolution time for tickets ──
    resolution_times = []
    for t in all_tickets:
        created = t.get("created_at", 0)
        updated = t.get("updated_at", 0)
        if created and updated > created and t.get("status") in ("resolved", "closed"):
            resolution_times.append((updated - created) / (1000 * 3600))  # hours
    avg_resolution_hours = round(
        sum(resolution_times) / len(resolution_times), 1
    ) if resolution_times else 0

    # ── Tech productivity (tickets closed/resolved per tech) ──
    tech_ticket_map: dict[str, int] = {}
    for t in all_tickets:
        uid = t.get("assigned_user_id", "")
        if uid and t.get("status") in ("resolved", "closed"):
            tech_ticket_map[uid] = tech_ticket_map.get(uid, 0) + 1

    all_users = await _sql("SELECT id, name FROM user")
    user_name_map = {u["id"]: u.get("name", "Unknown") for u in all_users}
    tech_closed = [
        {"user_name": user_name_map.get(uid, "Unknown"), "closed_count": count}
        for uid, count in sorted(tech_ticket_map.items(), key=lambda x: -x[1])
    ]

    # ── Top customers by revenue ──
    customer_revenue: dict[str, float] = {}
    for inv in all_invoices:
        cid = inv.get("customer_id", "")
        if inv.get("status") == "paid":
            customer_revenue[cid] = customer_revenue.get(cid, 0) + float(inv.get("total", 0))
    all_customers = await _sql("SELECT id, first_name, last_name FROM customer")
    cust_name_map = {
        c["id"]: f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
        for c in all_customers
    }
    top_customers = [
        {"customer_name": cust_name_map.get(cid, "Unknown"), "revenue": round(rev, 2)}
        for cid, rev in sorted(customer_revenue.items(), key=lambda x: -x[1])[:10]
    ]

    return {
        "revenue_by_month": revenue_by_month,
        "ticket_by_status": ticket_by_status,
        "invoice_by_status": invoice_by_status,
        "appointments_by_month": appt_by_month,
        "totals": {
            "total_revenue": round(total_revenue, 2),
            "total_tickets": total_tickets,
            "open_tickets": open_tickets,
            "total_sent": total_sent,
            "total_paid": total_paid,
            "outstanding_revenue": round(outstanding_revenue, 2),
            "avg_resolution_hours": avg_resolution_hours,
        },
        "tech_closed": tech_closed,
        "top_customers": top_customers,
    }


# ── AUDIT LOG endpoints ─────────────────────────────────────────


@app.get("/api/audit-log")
async def get_audit_log(
    limit: int = 100,
    entity: str = "",
    action: str = "",
    user: dict = Depends(require_role("admin")),
):
    """Get audit log entries. Admin only. Returns most recent first."""
    filters = []
    if entity:
        filters.append(f"entity = '{entity}'")
    if action:
        filters.append(f"action = '{action}'")
    where = " WHERE " + " AND ".join(filters) if filters else ""
    rows = await _sql(f"SELECT * FROM audit_log{where}")
    rows = _sort(rows, "created_at")
    return {"entries": rows[:limit]}


# ── AUTH middleware ────────────────────────────────────────────

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """FastAPI dependency that validates JWT and returns user dict."""
    if credentials is None:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Invalid token: no subject")

    rows = await _sql(f"SELECT * FROM user WHERE id = '{user_id}'")
    if not rows:
        raise HTTPException(401, "User not found")
    user = rows[0]
    # Extract tenant_id from JWT payload
    user["tenant_id"] = payload.get("tenant_id", "")
    if not user.get("active", False):
        raise HTTPException(403, "User account is disabled")

    return user


# ── AUTH endpoints ─────────────────────────────────────────────

@app.post("/api/auth/login")
async def login(body: LoginRequest):
    """Login with email + password, returns JWT token."""
    email = body.email
    password = body.password

    if not email or not password:
        raise HTTPException(400, "Email and password required")

    rows = await _sql(f"SELECT * FROM user WHERE email = '{email}'")
    if not rows:
        raise HTTPException(401, "Invalid email or password")

    user = rows[0]
    pw_hash = user.get("password_hash", "")

    if not pw_hash or not bcrypt.checkpw(password.encode(), pw_hash.encode()):
        raise HTTPException(401, "Invalid email or password")

    if not user.get("active", False):
        raise HTTPException(403, "Account is disabled")

    now = datetime.utcnow()

    # Look up tenant membership
    tenant_id = ""
    try:
        tm_rows = await _sql(f"SELECT * FROM tenant_members WHERE username = '{user['name']}'")
        if tm_rows:
            tenant_id = tm_rows[0]["tenant_id"]
    except Exception:
        pass

    token = jwt.encode(
        {
            "sub": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "tenant_id": tenant_id,
            "iat": now,
            "exp": now + timedelta(hours=settings.jwt_expire_hours),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    return {
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "tenant_id": tenant_id,
        },
    }


@app.get("/api/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    """Return current user info from JWT."""
    # Include tenant info
    tenant_info = {}
    if user.get("tenant_id"):
        try:
            trows = await _sql(f"SELECT * FROM tenants WHERE id = '{user['tenant_id']}'")
            if trows:
                tenant_info = trows[0]
        except Exception:
            pass
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "tenant_id": user.get("tenant_id", ""),
        "tenant": tenant_info,
    }

# ── TENANT endpoints ─────────────────────────────────────────


def _safe_id(id_str: str) -> str:
    """Validate an ID is safe for SQL interpolation. Raises 400 if not."""
    if not id_str or not id_str.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(400, "Invalid ID format")
    return id_str


@app.get("/api/tenants")
async def list_tenants(user: dict = Depends(require_role("admin"))):
    """List all tenants."""
    try:
        rows = await _sql("SELECT * FROM tenants")
        return {"tenants": rows}
    except Exception as e:
        logger.warning("Failed to list tenants: %s", e)
        return {"tenants": []}


@app.post("/api/tenants")
async def create_tenant(body: TenantCreate, user: dict = Depends(require_role("admin"))):
    """Create a new tenant."""
    name = body.name.strip()
    slug = body.slug.strip()
    if not name:
        raise HTTPException(400, "name is required")
    if not slug:
        slug = name.lower().replace(" ", "-").replace("[^a-z0-9-]", "")
    result = await _call("create_tenant", [name, slug])
    await _log_audit(user, "create", "tenant", name, f"slug={slug}")
    return {"ok": True}


@app.get("/api/tenants/{tenant_id}")
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


@app.put("/api/tenants/{tenant_id}")
async def update_tenant(tenant_id: str, body: TenantUpdate, user: dict = Depends(require_role("admin"))):
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


@app.delete("/api/tenants/{tenant_id}")
async def delete_tenant(tenant_id: str, user: dict = Depends(require_role("admin"))):
    """Delete a tenant and all its data."""
    await _call("delete_tenant", [tenant_id])
    await _log_audit(user, "delete", "tenant", tenant_id)
    return {"ok": True}


@app.post("/api/tenants/{tenant_id}/members")
async def add_tenant_member(tenant_id: str, body: TenantMemberAdd, user: dict = Depends(require_role("admin"))):
    """Add a member to a tenant."""
    username = body.username.strip()
    role = body.role.strip()
    if not username:
        raise HTTPException(400, "username is required")
    await _call("add_tenant_member", [tenant_id, username, role])
    await _log_audit(user, "add_member", "tenant_member", username, f"tenant={tenant_id}")
    return {"ok": True}


@app.delete("/api/tenants/{tenant_id}/members/{member_id}")
async def remove_tenant_member(tenant_id: str, member_id: str, user: dict = Depends(require_role("admin"))):
    """Remove a member from a tenant."""
    await _call("remove_tenant_member", [member_id])
    await _log_audit(user, "remove_member", "tenant_member", member_id)
    return {"ok": True}


@app.put("/api/tenants/{tenant_id}/members/{member_id}")
async def update_tenant_member_role(tenant_id: str, member_id: str, body: TenantMemberRoleUpdate, user: dict = Depends(require_role("admin"))):
    """Update member role within a tenant."""
    role = body.role.strip()
    await _call("update_tenant_member_role", [member_id, role])
    await _log_audit(user, "update_member", "tenant_member", member_id, f"role={role}")
    return {"ok": True}


@app.post("/api/tenants/migrate")
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
        await _call("add_tenant_member", [tid, u["name"], "admin" if u.get("role") == "admin" else "user"])
        count += 1
    tables = [
        "customer", "ticket", "ticket_note", "ticket_timer",
        "invoices", "invoice_line_items", "estimates", "estimate_line_items",
        "payment", "appointment", "products", "purchase_order",
        "purchase_order_line_item", "inventory_adjustment", "tax_rates",
        "audit_log", "custom_field_definitions", "customer_geolocations",
        "checklist_templates", "ticket_checklist_items", "webhook_subscriptions"
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
    return {"ok": True, "tenant_id": tid, "users_migrated": count, "tables_updated": updated}


@app.post("/api/auth/refresh-tenant")
async def refresh_token_tenant(user: dict = Depends(get_current_user)):
    """Refresh the JWT token with latest tenant_id from DB."""
    # Look up current tenant membership from DB
    tid = ""
    try:
        tm_rows = await _sql(f"SELECT * FROM tenant_members WHERE username = '{user['name']}'")
        if tm_rows:
            tid = tm_rows[0]["tenant_id"]
    except Exception:
        pass
    now = datetime.utcnow()
    token = jwt.encode(
        {
            "sub": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "tenant_id": tid,
            "iat": now,
            "exp": now + timedelta(hours=settings.jwt_expire_hours),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"token": token, "tenant_id": tid}




@app.post("/api/auth/set-password")
async def set_password(body: SetPasswordRequest, user: dict = Depends(get_current_user)):
    """Set/change password for current user."""
    pw = body.password
    if len(pw) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    await _call("set_user_password", [user["id"], hashed])
    return {"ok": True}


# ── USER endpoints ────────────────────────────────────────────

@app.get("/api/users")
async def list_users(user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    rows = await _sql("SELECT * FROM user")
    return {"users": _sort(rows, "name", desc=False)}


@app.post("/api/users")
async def create_user(body: UserCreate, user: dict = Depends(require_role("admin"))):
    await _call("create_user", [
        body.name,
        body.email,
        body.role,
    ])
    await _log_audit(user, "create", "user", body.email, f"role={body.role}")
    return {"ok": True}


# ── CUSTOMER PORTAL endpoints ────────────────────────────

async def get_current_customer(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """FastAPI dependency that validates customer JWT and returns customer dict."""
    if credentials is None:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

    if payload.get("type") != "customer":
        raise HTTPException(401, "Not a customer token")

    customer_id = payload.get("sub")
    if not customer_id:
        raise HTTPException(401, "Invalid token: no subject")

    rows = await _sql(f"SELECT * FROM customer WHERE id = '{customer_id}'")
    if not rows:
        raise HTTPException(401, "Customer not found")
    return rows[0]


@app.post("/api/portal/login")
async def portal_login(body: PortalLoginRequest):
    """Customer portal login with email + portal password."""
    email = body.email
    password = body.password

    if not email or not password:
        raise HTTPException(400, "Email and password required")

    rows = await _sql(f"SELECT * FROM customer WHERE email = '{email}'")
    if not rows:
        raise HTTPException(401, "Invalid email or password")

    customer = rows[0]
    pw_hash = customer.get("portal_password_hash", "")

    if not pw_hash or not bcrypt.checkpw(password.encode(), pw_hash.encode()):
        raise HTTPException(401, "Invalid email or password")

    now = datetime.utcnow()
    payload = {
        "sub": customer["id"],
        "tenant_id": customer.get("tenant_id", ""),
        "exp": now + timedelta(days=settings.jwt_expiry_days),
        "iat": now,
        "type": "portal",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {
        "token": token,
        "customer": {
            "id": customer["id"],
            "first_name": customer.get("first_name", ""),
            "last_name": customer.get("last_name", ""),
            "email": customer.get("email", ""),
            "tenant_id": customer.get("tenant_id", ""),
        },
    }


@app.get("/api/portal/me")
async def portal_me(customer: dict = Depends(get_current_customer)):
    """Return current customer info (safe fields only)."""
    return {
        "id": customer["id"],
        "first_name": customer.get("first_name", ""),
        "last_name": customer.get("last_name", ""),
        "email": customer["email"],
        "company": customer.get("company", ""),
        "phone": customer.get("phone", ""),
        "mobile": customer.get("mobile", ""),
        "address_line1": customer.get("address_line1", ""),
        "address_line2": customer.get("address_line2", ""),
        "city": customer.get("city", ""),
        "state": customer.get("state", ""),
        "zip": customer.get("zip", ""),
    }


@app.get("/api/portal/stats")
async def portal_stats(customer: dict = Depends(get_current_customer)):
    """Dashboard stats for the customer."""
    cid = customer["id"]
    tickets = await _sql(f"SELECT * FROM ticket WHERE customer_id = '{cid}'")
    invoices = await _sql(f"SELECT * FROM invoices WHERE customer_id = '{cid}'")
    appointments = await _sql(f"SELECT * FROM appointment WHERE customer_id = '{cid}'")
    open_tickets = sum(1 for t in tickets if t.get("status") not in ("resolved", "closed"))
    total_billed = sum(float(i.get("total", 0)) for i in invoices if i.get("status") not in ("cancelled", "draft"))
    total_paid = sum(float(i.get("total", 0)) for i in invoices if i.get("status") == "paid")
    upcoming = [a for a in appointments if a.get("start_time", 0) > 0]
    return {
        "total_tickets": len(tickets),
        "open_tickets": open_tickets,
        "total_invoices": len(invoices),
        "total_billed": total_billed,
        "total_paid": total_paid,
        "balance_due": total_billed - total_paid,
        "upcoming_appointments": len(upcoming),
    }


@app.get("/api/portal/tickets")
async def portal_tickets(customer: dict = Depends(get_current_customer)):
    """Customer's tickets."""
    rows = await _sql(f"SELECT * FROM ticket WHERE customer_id = '{customer['id']}'")
    # Also fetch assigned user names
    users = await _sql("SELECT * FROM user")
    user_map = {u["id"]: u["name"] for u in users}
    for t in rows:
        t["assigned_name"] = user_map.get(t.get("assigned_user_id", ""), "")
    return {"tickets": _sort(rows, "created_at")}


@app.get("/api/portal/tickets/{ticket_id}")
async def portal_ticket_detail(ticket_id: str, customer: dict = Depends(get_current_customer)):
    """Single ticket detail with notes (customer-owned only)."""
    rows = await _sql(f"SELECT * FROM ticket WHERE id = '{ticket_id}' AND customer_id = '{customer['id']}'")
    if not rows:
        raise HTTPException(404, "Ticket not found")
    ticket = rows[0]
    # Get notes (non-internal only for customer view)
    notes = await _sql(f"SELECT * FROM ticket_note WHERE ticket_id = '{ticket_id}' AND internal = false")
    ticket["notes"] = _sort(notes, "created_at", desc=False)
    # Get user names
    users = await _sql("SELECT * FROM user")
    user_map = {u["id"]: u["name"] for u in users}
    ticket["assigned_name"] = user_map.get(ticket.get("assigned_user_id", ""), "")
    return {"ticket": ticket}


@app.post("/api/portal/tickets/{ticket_id}/notes")
async def portal_add_note(ticket_id: str, body: PortalNoteCreate, customer: dict = Depends(get_current_customer)):
    """Customer adds a note to their ticket."""
    # Verify ownership
    rows = await _sql(f"SELECT * FROM ticket WHERE id = '{ticket_id}' AND customer_id = '{customer['id']}'")
    if not rows:
        raise HTTPException(404, "Ticket not found")
    await _call("add_ticket_note", [
        ticket_id,
        f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or "Customer",
        body.content,
        False,  # not internal
    ])
    return {"ok": True}


@app.get("/api/portal/invoices")
async def portal_invoices(customer: dict = Depends(get_current_customer)):
    """Customer's invoices."""
    rows = await _sql(f"SELECT * FROM invoices WHERE customer_id = '{customer['id']}'")
    return {"invoices": _sort(rows, "created_at")}


@app.get("/api/portal/invoices/{invoice_id}")
async def portal_invoice_detail(invoice_id: str, customer: dict = Depends(get_current_customer)):
    """Single invoice detail with line items (customer-owned only)."""
    rows = await _sql(f"SELECT * FROM invoices WHERE id = '{invoice_id}' AND customer_id = '{customer['id']}'")
    if not rows:
        raise HTTPException(404, "Invoice not found")
    inv = rows[0]
    items = await _sql(f"SELECT * FROM invoice_line_items WHERE invoice_id = '{invoice_id}'")
    inv["line_items"] = _sort(items, "sort_order", desc=False)
    # Get payments made on this invoice
    payments = await _sql(f"SELECT * FROM payment WHERE invoice_id = '{invoice_id}'")
    inv["payments"] = _sort(payments, "created_at")
    total_paid = sum(float(p.get("amount", 0)) for p in payments)
    inv["total_paid"] = total_paid
    inv["balance_due"] = float(inv.get("total", 0)) - total_paid
    return {"invoice": inv}


@app.post("/api/portal/payments")
async def portal_make_payment(body: PortalPaymentCreate, customer: dict = Depends(get_current_customer)):
    """Customer makes a payment on an invoice."""
    invoice_id = body.invoice_id
    amount = body.amount
    method = body.method

    # Verify invoice belongs to customer
    rows = await _sql(f"SELECT * FROM invoices WHERE id = '{invoice_id}' AND customer_id = '{customer['id']}'")
    if not rows:
        raise HTTPException(404, "Invoice not found")

    await _call("record_payment", [
        customer.get("tenant_id", ""),
        invoice_id,
        customer["id"],
        amount,
        method,
        body.reference,
        "Online payment via customer portal",
    ])

    # Auto-update invoice status
    payments = await _sql(f"SELECT * FROM payment WHERE invoice_id = '{invoice_id}'")
    inv = rows[0]
    total_paid = sum(float(p.get("amount", 0)) for p in payments)
    inv_total = float(inv.get("total", 0))
    new_status = "paid" if total_paid >= inv_total else "partial" if total_paid > 0 else inv.get("status", "draft")
    if new_status != inv.get("status"):
        await _call("update_invoice_status", [invoice_id, new_status])

    return {"ok": True}


@app.get("/api/portal/appointments")
async def portal_appointments(customer: dict = Depends(get_current_customer)):
    """Customer's appointments."""
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    rows = await _sql(f"SELECT * FROM appointment WHERE customer_id = '{customer['id']}'")
    upcoming = [a for a in rows if a.get("start_time", 0) > now_ms]
    past = [a for a in rows if a.get("start_time", 0) <= now_ms]
    return {
        "appointments": _sort(rows, "start_time", desc=False),
        "upcoming": _sort(upcoming, "start_time", desc=False),
        "past": _sort(past, "start_time", desc=False),
    }


@app.post("/api/portal/customer/set-password")
async def portal_set_password(body: PortalSetPassword, customer: dict = Depends(get_current_customer)):
    """Customer sets/changes their portal password."""
    pw = body.password
    if len(pw) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    await _call("set_customer_password", [customer["id"], hashed])
    return {"ok": True}


# ── STRIPE PAYMENT endpoints ─────────────────────────────


@app.post("/api/portal/payments/create-checkout-session")
async def portal_create_checkout_session(body: PortalCheckoutSessionCreate, customer: dict = Depends(get_current_customer)):
    """Create a Stripe Checkout Session for an invoice payment."""
    if not stripe_configured():
        raise HTTPException(503, "Stripe is not configured. Set STRIPE_SECRET_KEY in .env")

    invoice_id = body.invoice_id
    if not invoice_id:
        raise HTTPException(400, "invoice_id is required")

    # Verify invoice belongs to this customer
    rows = await _sql(f"SELECT * FROM invoices WHERE id = '{invoice_id}' AND customer_id = '{customer['id']}'")
    if not rows:
        raise HTTPException(404, "Invoice not found")
    inv = rows[0]

    if inv.get("status") in ("paid", "cancelled"):
        raise HTTPException(400, f"Invoice is already {inv['status']}")

    total = float(inv.get("total", 0))
    payments = await _sql(f"SELECT * FROM payment WHERE invoice_id = '{invoice_id}'")
    total_paid = sum(float(p.get("amount", 0)) for p in payments)
    amount_due = round(total - total_paid, 2)

    if amount_due <= 0:
        raise HTTPException(400, "Invoice is already fully paid")

    line_items = await _sql(f"SELECT * FROM invoice_line_items WHERE invoice_id = '{invoice_id}'")
    items_desc = "; ".join(f"{li.get('description','')} x{li.get('quantity',1)}" for li in line_items)

    result = await create_checkout_session(
        invoice_id=invoice_id,
        invoice_number=int(inv.get("invoice_number", 0)),
        customer_id=customer["id"],
        customer_email=customer.get("email", ""),
        amount=amount_due,
        line_items_desc=items_desc,
    )

    if not result:
        raise HTTPException(502, "Failed to create Stripe checkout session")

    return result


@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events (checkout.session.completed)."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    event = await verify_webhook(payload, sig_header)
    if not event:
        raise HTTPException(400, "Invalid webhook signature")

    event_type = event.get("type", "")
    logger.info("Stripe webhook received: %s", event_type)

    if event_type == "checkout.session.completed":
        session = event.get("data", {}).get("object", {})
        metadata = session.get("metadata", {})
        invoice_id = metadata.get("invoice_id", "")
        customer_id = metadata.get("customer_id", "")
        invoice_number = metadata.get("invoice_number", "")
        amount_total = float(session.get("amount_total", 0)) / 100.0
        payment_intent = session.get("payment_intent", "")
        stripe_session_id = session.get("id", "")

        if invoice_id and amount_total > 0:
            # Look up tenant_id from the invoice
            inv_rows = await _sql(f"SELECT tenant_id FROM invoices WHERE id = '{invoice_id}'")
            tid = inv_rows[0]["tenant_id"] if inv_rows else ""
            await _call("record_payment", [
                tid,
                invoice_id,
                customer_id,
                amount_total,
                "card",
                f"stripe_{payment_intent}",
                f"Stripe payment — session {stripe_session_id}",
            ])
            # Auto-update invoice status
            payments = await _sql(f"SELECT * FROM payment WHERE invoice_id = '{invoice_id}'")
            inv_rows = await _sql(f"SELECT * FROM invoices WHERE id = '{invoice_id}'")
            if inv_rows:
                inv = inv_rows[0]
                total_paid = sum(float(p.get("amount", 0)) for p in payments)
                total = float(inv.get("total", 0))
                new_status = "paid" if total_paid >= total else "partial"
                if new_status != inv.get("status"):
                    await _call("update_invoice_status", [invoice_id, new_status])

            logger.info("Stripe payment recorded for invoice %s: $%.2f", invoice_number, amount_total)

    return {"ok": True}


# ── CSV EXPORT ──────────────────────────────────────────────


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


@app.get("/api/export/{entity}")
async def export_csv(entity: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """Export all records of an entity type as CSV. Downloads as attachment."""
    table = ENTITY_TABLE_MAP.get(entity)
    if not table:
        raise HTTPException(400, f"Unknown entity: {entity}. Valid: {', '.join(ENTITY_TABLE_MAP)}")

    rows = await _sql(f"SELECT * FROM {table}")
    if not rows:
        return Response(
            content="",
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={entity}.csv"},
        )

    output = io.StringIO()
    fieldnames = sorted(rows[0].keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        d = {}
        for k in fieldnames:
            v = r.get(k)
            if v is None:
                d[k] = ""
            elif isinstance(v, bool):
                d[k] = "true" if v else "false"
            else:
                d[k] = str(v)
        writer.writerow(d)

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={entity}.csv"},
    )


# ── CSV IMPORT ──────────────────────────────────────────────


@app.post("/api/import/customers")
async def import_customers_csv(file: UploadFile = File(...), user: dict = Depends(require_role("admin"))):
    """Import customers from CSV.
    Required columns: first_name, last_name.
    Optional: email, phone, mobile, company, address_line1, address_line2, city, state, zip, notes, tags.
    If id column is provided, uses import_customer reducer to preserve IDs.
    Otherwise uses create_customer (generates new IDs).
    """
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    required = {"first_name", "last_name"}
    if not required.issubset(reader.fieldnames or []):
        raise HTTPException(400, f"CSV must contain columns: {', '.join(required)}")

    now_ms = int(datetime.utcnow().timestamp() * 1000)
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
                await _call("import_customer", [
                    user["tenant_id"],
                    cid, fn, ln, email, phone, mobile, addr1, addr2,
                    city, state, zipc, company, notes, tags,
                    created_at, updated_at,
                ])
            else:
                await _call("create_customer", [user["tenant_id"], fn, ln, email, phone])
            count += 1
        except Exception as e:
            errors.append(f"Row {i}: {e}")

    return {"imported": count, "errors": errors, "file": file.filename}


@app.post("/api/import/products")
async def import_products_csv(file: UploadFile = File(...), user: dict = Depends(require_role("admin"))):
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

    now_ms = int(datetime.utcnow().timestamp() * 1000)
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
                await _call("import_product", [
                    user["tenant_id"],
                    pid, name, sku, barcode, desc, category, price, cost,
                    qoh, qc, min_stock, location, active, created_at, updated_at,
                ])
            else:
                await _call("create_product", [user["tenant_id"], name, sku, barcode, desc, category, price, cost, qoh])
            count += 1
        except Exception as e:
            errors.append(f"Row {i}: {e}")

    return {"imported": count, "errors": errors, "file": file.filename}


# ── CUSTOM FIELDS endpoints ───────────────────────────────


@app.get("/api/custom-field-definitions")
async def list_custom_field_definitions(entity_type: str | None = None, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """List custom field definitions, optionally filtered by entity_type."""
    rows = await _sql_t("SELECT * FROM custom_field_definitions", user["tenant_id"])
    if entity_type:
        rows = [r for r in rows if r.get("entity_type") == entity_type]
    return {"definitions": rows}


@app.post("/api/custom-field-definitions")
async def create_custom_field_definition(body: CustomFieldDefinitionCreate, user: dict = Depends(require_role("admin"))):
    """Create a custom field definition."""
    field_id = secrets.token_hex(12)
    await _call("create_custom_field_definition", [
        user["tenant_id"],
        field_id,
        body.entity_type,
        body.label,
        body.field_type,
        json.dumps(body.options),
        body.sort_order,
        body.required,
        body.active,
    ])
    await _log_audit(user, "create", "custom_field_definition", field_id, body.label)
    return {"ok": True, "id": field_id}


@app.put("/api/custom-field-definitions/{field_id}")
async def update_custom_field_definition(field_id: str, body: CustomFieldDefinitionCreate, user: dict = Depends(require_role("admin"))):
    """Update a custom field definition."""
    await _call("update_custom_field_definition", [
        field_id,
        body.label,
        body.field_type,
        json.dumps(body.options),
        body.sort_order,
        body.required,
        body.active,
    ])
    await _log_audit(user, "update", "custom_field_definition", field_id, body.label)
    return {"ok": True}


@app.delete("/api/custom-field-definitions/{field_id}")
async def delete_custom_field_definition(field_id: str, user: dict = Depends(require_role("admin"))):
    """Delete a custom field definition."""
    await _call("delete_custom_field_definition", [field_id])
    await _log_audit(user, "delete", "custom_field_definition", field_id, "")
    return {"ok": True}


@app.get("/api/custom-field-values/{entity_id}")
async def get_custom_field_values(entity_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """Get all custom field values for an entity."""
    rows = await _sql(f"SELECT * FROM custom_field_values WHERE entity_id = '{entity_id}'")
    return {"values": rows}


@app.put("/api/custom-field-values/{entity_id}")
async def set_custom_field_values(entity_id: str, body: CustomFieldValuesUpdate, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """Set custom field values for an entity. Body: { values: { field_id: value, ... } }"""
    values = body.values
    for field_id, value in values.items():
        await _call("set_custom_field_value", [entity_id, field_id, str(value), user.get("tenant_id", "")])
    await _log_audit(user, "update", "custom_field_values", entity_id, f"{len(values)} fields")
    return {"ok": True, "count": len(values)}


# ── CHECKLIST TEMPLATE endpoints ─────────────────────────────

@app.get("/api/checklist-templates")
async def list_checklist_templates(user: dict = Depends(require_role("admin", "tech"))):
    """List all checklist templates."""
    rows = await _sql_t("SELECT * FROM checklist_templates", user["tenant_id"])
    return {"templates": _sort(rows, "name")}


@app.post("/api/checklist-templates")
async def create_checklist_template(body: ChecklistTemplateCreate, user: dict = Depends(require_role("admin"))):
    """Create a checklist template. Items: [{"label":"...","order":1}]"""
    await _call("create_checklist_template", [
        user["tenant_id"],
        body.name,
        body.description,
        json.dumps(body.items),
    ])
    await _log_audit(user, "create", "checklist_template", body.name)
    return {"ok": True}


@app.put("/api/checklist-templates/{template_id}")
async def update_checklist_template(template_id: str, body: ChecklistTemplateUpdate, user: dict = Depends(require_role("admin"))):
    """Update a checklist template."""
    await _call("update_checklist_template", [
        template_id,
        body.name,
        body.description,
        json.dumps(body.items),
    ])
    await _log_audit(user, "update", "checklist_template", template_id)
    return {"ok": True}


@app.delete("/api/checklist-templates/{template_id}")
async def delete_checklist_template(template_id: str, user: dict = Depends(require_role("admin"))):
    """Delete a checklist template."""
    await _call("delete_checklist_template", [template_id])
    await _log_audit(user, "delete", "checklist_template", template_id)
    return {"ok": True}


# ── TICKET CHECKLIST endpoints ────────────────────────────────

@app.get("/api/tickets/{ticket_id}/checklist")
async def get_ticket_checklist(ticket_id: str, user: dict = Depends(require_role("admin", "tech", "front_desk"))):
    """Get checklist items for a ticket."""
    rows = await _sql(f"SELECT * FROM ticket_checklist_items WHERE ticket_id = '{ticket_id}'")
    return {"items": _sort(rows, "sort_order")}


@app.post("/api/tickets/{ticket_id}/checklist/apply")
async def apply_checklist_to_ticket(ticket_id: str, body: ChecklistApply, user: dict = Depends(require_role("admin", "tech"))):
    """Apply a checklist template to a ticket."""
    template_id = body.template_id
    await _call("apply_checklist_template", [ticket_id, template_id])
    await _log_audit(user, "apply", "checklist", ticket_id, f"template={template_id}")
    return {"ok": True}


@app.put("/api/tickets/{ticket_id}/checklist/{item_id}")
async def update_checklist_item(ticket_id: str, item_id: str, body: ChecklistToggle, user: dict = Depends(require_role("admin", "tech"))):
    """Toggle a checklist item completed/uncompleted."""
    await _call("update_checklist_item", [item_id, body.completed])
    return {"ok": True}


@app.delete("/api/tickets/{ticket_id}/checklist")
async def delete_ticket_checklist(ticket_id: str, user: dict = Depends(require_role("admin", "tech"))):
    """Remove all checklist items from a ticket."""
    await _call("delete_ticket_checklist", [ticket_id])
    await _log_audit(user, "delete", "checklist", ticket_id)
    return {"ok": True}


# ── MAIL SETTINGS endpoints ──────────────────────────────


@app.get("/api/settings/mail")
async def mail_settings_get(user: dict = Depends(require_role("admin"))):
    """Get current mail settings (without password)."""
    settings = get_mail_settings()
    if settings is None:
        return {"configured": False, "settings": None}
    return {"configured": True, "settings": settings}


@app.post("/api/settings/mail")
async def mail_settings_save(body: MailSettingsUpdate, user: dict = Depends(require_role("admin"))):
    """Save mail settings."""
    # Map Pydantic field names to mail.py helper-expected keys
    data = {
        "host": body.smtp_host,
        "port": body.smtp_port,
        "username": body.smtp_user,
        "password": body.smtp_password,
        "sender_email": body.smtp_from_email,
        "sender_name": body.smtp_from_name,
        "use_tls": body.smtp_tls,
    }
    update_mail_settings(data)
    return {"ok": True}


@app.post("/api/settings/mail/test")
async def mail_settings_test(user: dict = Depends(require_role("admin"))):
    """Test SMTP connection with current settings."""
    result = test_mail_connection()
    return result


# ── SMS SETTINGS endpoints ──────────────────────────────


@app.get("/api/settings/sms")
async def sms_settings_get(user: dict = Depends(require_role("admin"))):
    """Get current SMS settings (without auth token)."""
    settings = get_sms_settings()
    if settings is None:
        return {"configured": False, "settings": None}
    return {"configured": True, "settings": settings}


@app.post("/api/settings/sms")
async def sms_settings_save(body: SMSSettingsUpdate, user: dict = Depends(require_role("admin"))):
    """Save SMS settings."""
    # Map Pydantic field names to sms.py helper-expected keys
    data = {
        "account_sid": body.twilio_account_sid,
        "auth_token": body.twilio_auth_token,
        "from_number": body.twilio_from_number,
    }
    update_sms_settings(data)
    return {"ok": True}


@app.post("/api/settings/sms/test")
async def sms_settings_test(user: dict = Depends(require_role("admin"))):
    """Test Twilio connection with current settings."""
    result = await test_sms_connection()
    return result


# ── WEBHOOK SUBSCRIPTION endpoints ─────────────────────────


@app.get("/api/webhook-subscriptions")
async def list_webhook_subscriptions(user: dict = Depends(require_role("admin"))):
    """List all webhook subscriptions."""
    rows = await _get_webhook_subscriptions()
    return {"subscriptions": rows}


@app.post("/api/webhook-subscriptions")
async def create_webhook_subscription(body: WebhookSubscriptionCreate, user: dict = Depends(require_role("admin"))):
    """Create a new webhook subscription."""
    url = body.url.strip()
    events = body.events.strip()
    secret = body.secret.strip()

    if not url:
        raise HTTPException(400, "url is required")
    if not events:
        raise HTTPException(400, "events is required")

    # Validate events
    valid_events = set(WEBHOOK_EVENTS)
    given_events = {e.strip() for e in events.split(",") if e.strip()}
    invalid = given_events - valid_events
    if invalid:
        raise HTTPException(400, f"Invalid event(s): {', '.join(invalid)}")

    await _call("create_webhook_subscription", [user["tenant_id"], url, events, secret])
    await _log_audit(user, "create", "webhook_subscription", url, events)
    return {"ok": True}


@app.put("/api/webhook-subscriptions/{sub_id}")
async def update_webhook_subscription(sub_id: str, body: WebhookSubscriptionUpdate, user: dict = Depends(require_role("admin"))):
    """Update a webhook subscription."""
    url = body.url.strip()
    events = body.events.strip()
    secret = body.secret.strip()
    active = body.active

    if not url:
        raise HTTPException(400, "url is required")

    # Validate events if provided
    if events:
        valid_events = set(WEBHOOK_EVENTS)
        given_events = {e.strip() for e in events.split(",") if e.strip()}
        invalid = given_events - valid_events
        if invalid:
            raise HTTPException(400, f"Invalid event(s): {', '.join(invalid)}")

    await _call("update_webhook_subscription", [sub_id, url, events, secret, active])
    await _log_audit(user, "update", "webhook_subscription", url, events)
    return {"ok": True}


@app.delete("/api/webhook-subscriptions/{sub_id}")
async def delete_webhook_subscription(sub_id: str, user: dict = Depends(require_role("admin"))):
    """Delete a webhook subscription."""
    await _call("delete_webhook_subscription", [sub_id])
    await _log_audit(user, "delete", "webhook_subscription", sub_id)
    return {"ok": True}


@app.post("/api/webhook-subscriptions/{sub_id}/test")
async def test_webhook_subscription(sub_id: str, user: dict = Depends(require_role("admin"))):
    """Send a test event to a specific subscription."""
    rows = await _sql(f"SELECT * FROM webhook_subscriptions WHERE id = '{sub_id}'")
    if not rows:
        raise HTTPException(404, "Subscription not found")
    sub = rows[0]
    test_payload = {
        "entity_type": "test",
        "id": "test_001",
        "message": "This is a test webhook event from SpacetimeCRM.",
    }
    from webhooks import _deliver
    result = await _deliver(
        url=sub["url"],
        event_type="test.ping",
        payload=test_payload,
        secret=sub.get("secret", ""),
        max_retries=1,
    )
    return result


# ── HEALTH CHECKS ─────────────────────────────────────────


@app.get("/api/health")
async def health_check():
    """Health check endpoint — verifies server and STDB connectivity."""
    results: dict = {"server": "ok", "stdb": "unknown", "module": "unknown"}
    http_code = 200

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                settings.stdb_sql_url,
                content="SELECT 1 AS ok",
                headers={"Content-Type": "application/sql"},
            )
            if resp.status_code < 500:
                results["stdb"] = "ok"
                # Check that tables exist (module is published)
                tr = await client.post(
                    settings.stdb_sql_url,
                    content="SELECT COUNT(*) AS c FROM customer",
                    headers={"Content-Type": "application/sql"},
                )
                if tr.status_code < 500:
                    results["module"] = "ok"
                else:
                    # Module hasn't been published yet; try any known table
                    tr2 = await client.post(
                        settings.stdb_sql_url,
                        content="SELECT 1 AS ok FROM user LIMIT 1",
                        headers={"Content-Type": "application/sql"},
                    )
                    results["module"] = "ok" if tr2.status_code < 500 else "not published"
            else:
                results["stdb"] = f"error: {resp.status_code}"
                http_code = 503
    except Exception as e:
        results["stdb"] = f"unreachable: {e}"
        http_code = 503

    from fastapi.responses import JSONResponse
    return JSONResponse(content=results, status_code=http_code)


@app.get("/api/health/ready")
async def health_ready():
    """Readiness probe — STDB must be connected."""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.post(
                settings.stdb_sql_url,
                content="SELECT 1",
                headers={"Content-Type": "application/sql"},
            )
            if resp.status_code < 500:
                return {"status": "ok"}
    except Exception:
        pass
    return {"status": "unavailable"}


ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "web" / "dist"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"detail": "Not Found"}


# ── ENTRY ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.server_port, reload=False)
