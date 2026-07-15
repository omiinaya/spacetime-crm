#!/usr/bin/env python3
"""Seed demo data into SpacetimeCRM."""

import httpx
import json
import sys

BASE = "http://localhost:8723"
ADMIN_EMAIL = "admin@crm.local"
ADMIN_PW = os.environ.get("CRM_ADMIN_PW", "change-me-in-production")

# Login
resp = httpx.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW})
resp.raise_for_status()
TOKEN = resp.json()["token"]
H = {"Authorization": f"Bearer {TOKEN}"}
C = httpx.Client(headers=H, base_url=BASE)


def ok(r):
    return r.status_code == 200


# ── Customers ──
customers = [
    (
        "Alice",
        "Johnson",
        "alice@example.com",
        "555-1001",
        "TechCorp",
        "100 Main St",
        "Portland",
        "OR",
        "97201",
    ),
    (
        "Bob",
        "Williams",
        "bob@example.com",
        "555-1002",
        "Bob's Repair",
        "200 Oak Ave",
        "Portland",
        "OR",
        "97202",
    ),
    (
        "Carol",
        "Davis",
        "carol@example.com",
        "555-1003",
        "",
        "300 Pine Rd",
        "Beaverton",
        "OR",
        "97005",
    ),
    (
        "David",
        "Miller",
        "david@example.com",
        "555-1004",
        "Miller LLC",
        "400 Elm St",
        "Hillsboro",
        "OR",
        "97123",
    ),
    (
        "Eve",
        "Wilson",
        "eve@example.com",
        "555-1005",
        "",
        "500 Cedar Ln",
        "Portland",
        "OR",
        "97203",
    ),
]
cust_ids = []
for fname, lname, email, phone, company, addr, city, state, zip_code in customers:
    r = C.post(
        "/api/customers",
        json={
            "first_name": fname,
            "last_name": lname,
            "email": email,
            "phone": phone,
            "company": company,
            "address_line1": addr,
            "city": city,
            "state": state,
            "zip": zip_code,
            "mobile": phone,
        },
    )
    if ok(r):
        # Fetch the customer back to get the STDB-assigned ID
        r2 = C.get(f"/api/customers?search={email}")
        items = r2.json().get("customers", [])
        if items:
            cust_ids.append(items[0]["id"])
        print(f"  ✅ Customer: {fname} {lname}")

# Set portal password for Alice
r = C.post(f"/api/customers/{cust_ids[0]}/portal-password", json={"password": "alice123"})
print(f"  ✅ Portal password set for Alice: {ok(r)}")

# ── Products ──
products = [
    ("Screen Repair", "SCR-001", 89.99, 15.00, 50, 10),
    ("Battery Replacement", "BAT-001", 49.99, 8.00, 30, 5),
    ("Charging Port Repair", "CHG-001", 69.99, 12.00, 20, 5),
    ("Water Damage Cleanup", "WTR-001", 149.99, 25.00, 15, 3),
    ("Data Recovery", "DAT-001", 99.99, 0.00, 99, 1),
    ("Screen Protector", "ACC-001", 19.99, 3.00, 100, 20),
    ("Phone Case", "ACC-002", 29.99, 8.00, 75, 15),
    ("Cable USB-C", "CBL-001", 9.99, 2.00, 200, 50),
]
prod_ids = []
for name, sku, price, cost, stock, min_stock in products:
    r = C.post(
        "/api/products",
        json={
            "name": name,
            "sku": sku,
            "price": price,
            "cost": cost,
            "quantity_on_hand": stock,
            "min_stock": min_stock,
            "active": True,
        },
    )
    if ok(r):
        prod_ids.append(r.json().get("id", ""))
        print(f"  ✅ Product: {name}")

# ── Tickets ──
tickets = [
    (0, "iPhone 15", "Broken screen, needs replacement", "in_progress", "high"),
    (1, "Samsung Galaxy S24", "Battery drains quickly", "new", "medium"),
    (2, "Google Pixel 8", "Charging port not working", "assigned", "high"),
    (3, "iPhone 14", "Water damage, won't turn on", "waiting_on_customer", "urgent"),
    (0, "iPad Air", "Cracked screen corner", "resolved", "low"),
    (4, "MacBook Pro", "Data recovery from failed SSD", "new", "medium"),
]
ticket_ids = []
for ci, device, issue, status, priority in tickets:
    r = C.post(
        "/api/tickets",
        json={
            "customer_id": cust_ids[ci],
            "device_type": device.split()[0],
            "device_model": device,
            "title": f"{device} - {issue[:30]}",
            "description": issue,
            "status": status,
            "priority": priority,
        },
    )
    if ok(r):
        ticket_ids.append(r.json().get("id", ""))
        print(f"  ✅ Ticket: {device} ({status})")

# ── Invoices ──
inv_items_data = [
    (0, 0, [("Screen Repair", "SCR-001", 1, 89.99)]),
    (2, 2, [("Charging Port Repair", "CHG-001", 1, 69.99)]),
    (4, 5, [("Data Recovery", "DAT-001", 1, 99.99)]),
]
for ci, ti, items in inv_items_data:
    r = C.post(
        "/api/invoices",
        json={
            "customer_id": cust_ids[ci],
            "ticket_id": ticket_ids[ti] if ti < len(ticket_ids) else "",
            "subtotal": sum(q * p for _, _, q, p in items),
            "total": sum(q * p for _, _, q, p in items),
            "status": "sent",
            "notes": "Demo invoice",
        },
    )
    inv_data = r.json()
    print(f"  ✅ Invoice created: HTTP {r.status_code}")
    # Get the invoice ID from the list
    r2 = C.get("/api/invoices")
    invoices = r2.json().get("invoices", [])
    if invoices:
        inv_id = invoices[0]["id"]
        for desc, _, qty, price in items:
            C.post(
                f"/api/invoices/{inv_id}/line-items",
                json={
                    "item_type": "product",
                    "description": desc,
                    "quantity": qty,
                    "unit_price": price,
                    "total": qty * price,
                },
            )

# ── Payments ──
r = C.get("/api/invoices")
invoices = r.json().get("invoices", [])
if invoices:
    C.post(
        "/api/payments",
        json={
            "invoice_id": invoices[-1]["id"],
            "customer_id": invoices[-1].get("customer_id", ""),
            "amount": 49.99,
            "method": "card",
            "notes": "Partial payment",
        },
    )
    print(f"  ✅ Payment recorded")

# ── Appointments ──
import time

now = int(time.time() * 1000)
appts = [
    (
        0,
        "iPhone 15 Screen Repair",
        now + 86400000,
        now + 86400000 + 3600000,
        "scheduled",
    ),
    (
        1,
        "Galaxy Battery Check",
        now + 172800000,
        now + 172800000 + 1800000,
        "scheduled",
    ),
    (
        2,
        "Charging Port Diagnosis",
        now - 86400000,
        now - 86400000 + 3600000,
        "completed",
    ),
]
for ci, title, start, end, status in appts:
    r = C.post(
        "/api/appointments",
        json={
            "customer_id": cust_ids[ci],
            "title": title,
            "start_time": start,
            "end_time": end,
            "status": status,
        },
    )
    if ok(r):
        print(f"  ✅ Appointment: {title}")

# ── Verify ──
print("\n=== VERIFICATION ===")
for table in [
    "customers",
    "products",
    "tickets",
    "invoices",
    "payments",
    "appointments",
]:
    r = C.get(f"/api/{table}")
    count = len(r.json().get(table if table != "products" else table, r.json().get(table.rstrip("s"), [])))
    print(f"  {table}: {count}")

print("\n✅ Demo data seeded!")
