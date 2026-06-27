import json
import logging
from typing import Any
from pathlib import Path
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from config import settings
import bcrypt
import jwt
from datetime import datetime, timedelta
import secrets
from fastapi import Depends, HTTPException, status
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
    allow_origins=["*"],
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
    return sorted(rows, key=lambda r: r.get(key, 0) or 0, reverse=desc)


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


# ── CUSTOMER endpoints ────────────────────────────────────────

@app.get("/api/customers")
async def list_customers(search: str = ""):
    rows = await _sql("SELECT * FROM customer")
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
async def create_customer(body: dict):
    await _call("create_customer", [
        body.get("first_name", ""),
        body.get("last_name", ""),
        body.get("email", ""),
        body.get("phone", ""),
    ])
    return {"ok": True}


@app.put("/api/customers/{customer_id}")
async def update_customer(customer_id: str, body: dict):
    await _call("update_customer", [
        customer_id,
        body.get("first_name", ""),
        body.get("last_name", ""),
        body.get("email", ""),
        body.get("phone", ""),
        body.get("mobile", ""),
        body.get("address_line1", ""),
        body.get("address_line2", ""),
        body.get("city", ""),
        body.get("state", ""),
        body.get("zip", ""),
        body.get("company", ""),
        body.get("notes", ""),
        body.get("tags", ""),
    ])
    return {"ok": True}


@app.delete("/api/customers/{customer_id}")
async def delete_customer(customer_id: str):
    await _call("delete_customer", [customer_id])
    return {"ok": True}


# ── TICKET endpoints ──────────────────────────────────────────

@app.get("/api/tickets")
async def list_tickets(status: str = ""):
    rows = await _sql("SELECT * FROM ticket")
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return {"tickets": _sort(rows, "created_at")}


@app.post("/api/tickets")
async def create_ticket(body: dict):
    await _call("create_ticket", [
        body.get("customer_id", ""),
        body.get("title", ""),
        body.get("description", ""),
        body.get("device_type", ""),
        body.get("device_model", ""),
        body.get("device_serial", ""),
        body.get("priority", "normal"),
    ])
    return {"ok": True}


@app.put("/api/tickets/{ticket_id}/status")
async def update_ticket_status(ticket_id: str, body: dict):
    await _call("update_ticket_status", [ticket_id, body.get("status", "")])
    return {"ok": True}


@app.put("/api/tickets/{ticket_id}/assign")
async def assign_ticket(ticket_id: str, body: dict):
    await _call("assign_ticket", [ticket_id, body.get("assigned_user_id", "")])
    return {"ok": True}


@app.get("/api/tickets/{ticket_id}/notes")
async def get_ticket_notes(ticket_id: str):
    rows = await _sql(f"SELECT * FROM ticket_note WHERE ticket_id = '{ticket_id}'")
    return {"notes": _sort(rows, "created_at", desc=False)}


@app.post("/api/tickets/{ticket_id}/notes")
async def add_ticket_note(ticket_id: str, body: dict):
    await _call("add_ticket_note", [
        ticket_id,
        body.get("author", ""),
        body.get("content", ""),
        body.get("internal", False),
    ])
    return {"ok": True}


@app.delete("/api/tickets/{ticket_id}")
async def delete_ticket(ticket_id: str):
    await _call("delete_ticket", [ticket_id])
    return {"ok": True}


# ── TICKET TIMER endpoints ────────────────────────────────────

@app.get("/api/tickets/{ticket_id}/timers")
async def get_ticket_timers(ticket_id: str):
    rows = await _sql(f"SELECT * FROM ticket_timer WHERE ticket_id = '{ticket_id}'")
    return {"timers": _sort(rows, "start_time")}


@app.get("/api/timers")
async def list_all_timers(user_id: str = "", running: str = ""):
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


@app.post("/api/tickets/{ticket_id}/timers/start")
async def start_ticket_timer(ticket_id: str, body: dict):
    await _call("start_ticket_timer", [ticket_id, body.get("user_id", "")])
    return {"ok": True}


@app.post("/api/timers/{timer_id}/stop")
async def stop_ticket_timer(timer_id: str):
    await _call("stop_ticket_timer", [timer_id])
    return {"ok": True}


@app.delete("/api/timers/{timer_id}")
async def delete_ticket_timer(timer_id: str):
    await _call("delete_ticket_timer", [timer_id])
    return {"ok": True}


# ── INVOICE endpoints ─────────────────────────────────────────

@app.get("/api/invoices")
async def list_invoices(status: str = ""):
    rows = await _sql("SELECT * FROM invoices")
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return {"invoices": _sort(rows, "created_at")}


@app.post("/api/invoices")
async def create_invoice(body: dict):
    await _call("create_invoice", [
        body.get("customer_id", ""),
        body.get("ticket_id", ""),
        body.get("notes", ""),
        body.get("terms", ""),
        body.get("due_date", 0),
    ])
    return {"ok": True}


@app.put("/api/invoices/{invoice_id}/status")
async def update_invoice_status(invoice_id: str, body: dict):
    await _call("update_invoice_status", [invoice_id, body.get("status", "")])
    return {"ok": True}


@app.get("/api/invoices/{invoice_id}/line-items")
async def get_invoice_line_items(invoice_id: str):
    rows = await _sql(f"SELECT * FROM invoice_line_items WHERE invoice_id = '{invoice_id}'")
    return {"line_items": _sort(rows, "sort_order", desc=False)}


@app.post("/api/invoices/{invoice_id}/line-items")
async def add_invoice_line_item(invoice_id: str, body: dict):
    await _call("add_invoice_line_item", [
        invoice_id,
        body.get("item_type", "service"),
        body.get("description", ""),
        body.get("quantity", 1),
        body.get("unit_price", 0),
    ])
    return {"ok": True}


@app.delete("/api/invoices/{invoice_id}/line-items/{item_id}")
async def delete_invoice_line_item(invoice_id: str, item_id: str):
    await _call("delete_invoice_line_item", [item_id])
    return {"ok": True}


@app.delete("/api/invoices/{invoice_id}")
async def delete_invoice(invoice_id: str):
    await _call("delete_invoice", [invoice_id])
    return {"ok": True}


@app.get("/api/invoices/{invoice_id}/pdf")
async def invoice_pdf(invoice_id: str):
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
async def list_payments(invoice_id: str = ""):
    rows = await _sql("SELECT * FROM payment")
    if invoice_id:
        rows = [r for r in rows if r.get("invoice_id") == invoice_id]
    return {"payments": _sort(rows, "created_at")}


@app.post("/api/payments")
async def record_payment(body: dict):
    invoice_id = body.get("invoice_id", "")
    await _call("record_payment", [
        invoice_id,
        body.get("customer_id", ""),
        body.get("amount", 0),
        body.get("method", "cash"),
        body.get("reference", ""),
        body.get("notes", ""),
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
    return {"ok": True}


@app.delete("/api/payments/{payment_id}")
async def delete_payment(payment_id: str):
    await _call("delete_payment", [payment_id])
    return {"ok": True}


# ── APPOINTMENT endpoints ─────────────────────────────────────

@app.get("/api/appointments")
async def list_appointments():
    rows = await _sql("SELECT * FROM appointment")
    return {"appointments": _sort(rows, "start_time", desc=False)}


@app.post("/api/appointments")
async def create_appointment(body: dict):
    await _call("create_appointment", [
        body.get("customer_id", ""),
        body.get("ticket_id", ""),
        body.get("title", ""),
        body.get("description", ""),
        body.get("start_time", 0),
        body.get("end_time", 0),
        body.get("all_day", False),
    ])
    return {"ok": True}


@app.put("/api/appointments/{appt_id}/status")
async def update_appointment_status(appt_id: str, body: dict):
    await _call("update_appointment_status", [appt_id, body.get("status", "")])
    return {"ok": True}


@app.delete("/api/appointments/{appt_id}")
async def delete_appointment(appt_id: str):
    await _call("delete_appointment", [appt_id])
    return {"ok": True}


# ── PRODUCT endpoints ─────────────────────────────────────────

@app.get("/api/products")
async def list_products(search: str = ""):
    rows = await _sql("SELECT * FROM product")
    q = search.lower().strip()
    if q:
        rows = [
            r for r in rows
            if q in (r.get("name") or "").lower()
            or q in (r.get("sku") or "").lower()
        ]
    return {"products": _sort(rows, "name", desc=False)}


@app.post("/api/products")
async def create_product(body: dict):
    await _call("create_product", [
        body.get("name", ""),
        body.get("sku", ""),
        body.get("description", ""),
        body.get("category", ""),
        body.get("price", 0),
        body.get("cost", 0),
        body.get("quantity_on_hand", 0),
    ])
    return {"ok": True}


@app.put("/api/products/{product_id}/quantity")
async def update_product_quantity(product_id: str, body: dict):
    await _call("update_product_quantity", [product_id, body.get("quantity_on_hand", 0)])
    return {"ok": True}


@app.delete("/api/products/{product_id}")
async def delete_product(product_id: str):
    await _call("delete_product", [product_id])
    return {"ok": True}


# ── ESTIMATE endpoints ────────────────────────────────────────

@app.get("/api/estimates")
async def list_estimates(status: str = ""):
    rows = await _sql("SELECT * FROM estimates")
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return {"estimates": _sort(rows, "created_at")}


@app.post("/api/estimates")
async def create_estimate(body: dict):
    await _call("create_estimate", [
        body.get("customer_id", ""),
        body.get("ticket_id", ""),
        body.get("notes", ""),
        body.get("expires_at", 0),
    ])
    return {"ok": True}


@app.put("/api/estimates/{estimate_id}/status")
async def update_estimate_status(estimate_id: str, body: dict):
    await _call("update_estimate_status", [estimate_id, body.get("status", "")])
    return {"ok": True}


@app.get("/api/estimates/{estimate_id}/line-items")
async def get_estimate_line_items(estimate_id: str):
    rows = await _sql(f"SELECT * FROM estimate_line_items WHERE estimate_id = '{estimate_id}'")
    return {"line_items": _sort(rows, "sort_order", desc=False)}


@app.post("/api/estimates/{estimate_id}/line-items")
async def add_estimate_line_item(estimate_id: str, body: dict):
    await _call("add_estimate_line_item", [
        estimate_id,
        body.get("item_type", "service"),
        body.get("description", ""),
        body.get("quantity", 1),
        body.get("unit_price", 0),
    ])
    return {"ok": True}


@app.delete("/api/estimates/{estimate_id}")
async def delete_estimate(estimate_id: str):
    await _call("delete_estimate", [estimate_id])
    return {"ok": True}


@app.post("/api/estimates/{estimate_id}/convert")
async def convert_estimate(estimate_id: str):
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

    return {"ok": True, "invoice_id": inv_id}


# ── PURCHASE ORDER endpoints ──────────────────────────────────

@app.get("/api/purchase-orders")
async def list_purchase_orders():
    rows = await _sql("SELECT * FROM purchase_order")
    return {"purchase_orders": _sort(rows, "created_at")}


@app.post("/api/purchase-orders")
async def create_purchase_order(body: dict):
    await _call("create_purchase_order", [
        body.get("vendor_name", ""),
        body.get("notes", ""),
    ])
    return {"ok": True}


@app.delete("/api/purchase-orders/{po_id}")
async def delete_purchase_order(po_id: str):
    await _call("delete_purchase_order", [po_id])
    return {"ok": True}


# ── DASHBOARD stats ───────────────────────────────────────────

@app.get("/api/stats")
async def dashboard_stats():
    all_customers = await _sql("SELECT * FROM customer")
    all_tickets = await _sql("SELECT * FROM ticket")
    all_invoices = await _sql("SELECT * FROM invoices")
    all_appointments = await _sql("SELECT * FROM appointment")
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
    if not user.get("active", False):
        raise HTTPException(403, "User account is disabled")

    return user


# ── AUTH endpoints ─────────────────────────────────────────────

@app.post("/api/auth/login")
async def login(body: dict):
    """Login with email + password, returns JWT token."""
    email = body.get("email", "")
    password = body.get("password", "")

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
    token = jwt.encode(
        {
            "sub": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
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
        },
    }


@app.get("/api/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    """Return current user info from JWT."""
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
    }


@app.post("/api/auth/set-password")
async def set_password(body: dict, user: dict = Depends(get_current_user)):
    """Set/change password for current user."""
    pw = body.get("password", "")
    if len(pw) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    await _call("set_user_password", [user["id"], hashed])
    return {"ok": True}


# ── USER endpoints ────────────────────────────────────────────

@app.get("/api/users")
async def list_users():
    rows = await _sql("SELECT * FROM user")
    return {"users": _sort(rows, "name", desc=False)}


@app.post("/api/users")
async def create_user(body: dict):
    await _call("create_user", [
        body.get("name", ""),
        body.get("email", ""),
        body.get("role", "staff"),
    ])
    return {"ok": True}


# ── STATIC FILE SERVING (SPA) ─────────────────────────────────

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
    uvicorn.run("main:app", host="0.0.0.0", port=settings.server_port, reload=True)
