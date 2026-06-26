import json
import logging
from typing import Any
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings

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


# ── PAYMENT endpoints ─────────────────────────────────────────

@app.get("/api/payments")
async def list_payments(invoice_id: str = ""):
    rows = await _sql("SELECT * FROM payment")
    if invoice_id:
        rows = [r for r in rows if r.get("invoice_id") == invoice_id]
    return {"payments": _sort(rows, "created_at")}


@app.post("/api/payments")
async def record_payment(body: dict):
    await _call("record_payment", [
        body.get("invoice_id", ""),
        body.get("customer_id", ""),
        body.get("amount", 0),
        body.get("method", "cash"),
        body.get("reference", ""),
        body.get("notes", ""),
    ])
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
