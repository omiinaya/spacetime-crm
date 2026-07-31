"""Concurrent / multi-user tenant isolation integration tests.

Closes the ROADMAP test-quality gap "No concurrent/multi-user tests
for tenant isolation" by exercising the app with TWO fully independent
tenants (A = the standard ``isolated_tenant`` fixture, B = the new
``second_isolated_tenant`` fixture), each with its own admin JWT.

For the core entity types (customers, tickets, invoices) it verifies:

1. Cross-tenant list SELECTs return no foreign rows.
2. Cross-tenant direct entity fetch by ID returns 404.
3. Cross-tenant mutations via known IDs are rejected (404) and leave
   the target row completely untouched.
4. A concurrent burst of parallel list requests (``asyncio.gather``)
   leaks no cross-tenant data and produces no 5xx responses.

Requires live STDB (:3001) + backend (:8723) — same as the rest of the
integration suite.
"""

import asyncio

import httpx
import pytest

from .conftest import (
    SERVER_URL,
    _stdb_sql,
    _track_entity,
    assert_ok,
    create_customer,
)

# ── Helpers ─────────────────────────────────────────────────────────


def _row_ids(payload: dict, key: str) -> set[str]:
    """Collect the entity ids from a list payload (e.g. payload["tickets"])."""
    return {row.get("id") for row in payload.get(key, [])}


def _get_invoice_status(headers: dict, invoice_id: str) -> str:
    """Read an invoice's status via the (tenant-scoped) list endpoint."""
    resp = httpx.get(f"{SERVER_URL}/api/invoices", headers=headers, timeout=10)
    data = assert_ok(resp)
    for inv in data.get("invoices", []):
        if inv.get("id") == invoice_id:
            return inv.get("status", "")
    raise AssertionError(f"Invoice {invoice_id} not visible to caller")


@pytest.fixture(scope="session")
def isolation_data(
    test_admin_headers: dict,
    second_tenant_headers: dict,
    session_suffix: str,
) -> dict:
    """Entity set used by the isolation tests.

    Creates a customer + ticket + invoice inside tenant A (plus one
    customer inside tenant B so B's token is proven to work and B's
    lists are non-vacuous). Returns the IDs and the original field
    values so tests can assert cross-tenant access is rejected AND the
    underlying rows are never modified.
    """
    tag = f"iso-{session_suffix}"

    # ── Tenant A entities ──
    a_email = f"{tag}-a@example.com"
    a_customer = create_customer(
        test_admin_headers,
        session_suffix=session_suffix,
        first_name="Isolation",
        last_name="TenantA",
        email=a_email,
    )
    assert a_customer.get("id"), f"Tenant A customer creation failed: {a_customer}"
    a_customer_id = a_customer["id"]

    # Ticket linked to A's customer
    device_serial = f"SN-{tag}-A"
    resp = httpx.post(
        f"{SERVER_URL}/api/tickets",
        json={
            "customer_id": a_customer_id,
            "title": "Isolation ticket A",
            "description": "tenant isolation fixture",
            "device_type": "Phone",
            "device_model": "X",
            "device_serial": device_serial,
            "priority": "medium",
        },
        headers=test_admin_headers,
        timeout=10,
    )
    assert_ok(resp)
    rows = _stdb_sql(f"SELECT * FROM ticket WHERE device_serial = '{device_serial}'")
    assert rows and rows[0]["rows"], f"Ticket A not found by serial {device_serial}"
    a_ticket_id = rows[0]["rows"][0][0]
    _track_entity("ticket", a_ticket_id)

    # Invoice linked to A's customer
    resp = httpx.post(
        f"{SERVER_URL}/api/invoices",
        json={
            "customer_id": a_customer_id,
            "ticket_id": a_ticket_id,
            "notes": f"{tag}-invoice",
            "terms": "Due on receipt",
            "due_date": 1893456000000,  # 2030-01-01
        },
        headers=test_admin_headers,
        timeout=10,
    )
    assert_ok(resp)
    rows = _stdb_sql(
        f"SELECT * FROM invoices WHERE customer_id = '{a_customer_id}' AND notes = '{tag}-invoice'"
    )
    assert rows and rows[0]["rows"], "Invoice A not found"
    a_invoice_id = rows[0]["rows"][0][0]
    _track_entity("invoice", a_invoice_id)

    # Capture original values (through A's own scoped endpoints)
    tdata = httpx.get(
        f"{SERVER_URL}/api/tickets/{a_ticket_id}", headers=test_admin_headers, timeout=10
    ).json()["ticket"]
    a_ticket_status = tdata["status"]

    # ── Tenant B entity (proves B's token works; makes B's lists real) ──
    b_email = f"{tag}-b@example.com"
    b_customer = create_customer(
        second_tenant_headers,
        session_suffix=session_suffix,
        first_name="Isolation",
        last_name="TenantB",
        email=b_email,
    )
    assert b_customer.get("id"), f"Tenant B customer creation failed: {b_customer}"

    return {
        "customer_id": a_customer_id,
        "customer_email": a_email,
        "customer_first_name": "Isolation",
        "ticket_id": a_ticket_id,
        "ticket_status": a_ticket_status,
        "invoice_id": a_invoice_id,
        "invoice_status": _get_invoice_status(test_admin_headers, a_invoice_id),
        "b_customer_id": b_customer["id"],
        "b_customer_email": b_email,
    }


# ── 1. Cross-tenant list SELECTs ────────────────────────────────────


class TestCrossTenantListIsolation:
    """Tenant B must never see tenant A's rows in list endpoints."""

    def test_customer_list_does_not_leak(
        self, isolation_data: dict, test_admin_headers: dict, second_tenant_headers: dict
    ):
        data = isolation_data
        # B searches for A's exact unique email → must be empty
        resp = httpx.get(
            f"{SERVER_URL}/api/customers",
            params={"search": data["customer_email"]},
            headers=second_tenant_headers,
            timeout=10,
        )
        payload = assert_ok(resp)
        assert payload.get("customers", []) == [], (
            f"Tenant B saw tenant A's customer: {payload.get('customers', [])}"
        )
        # B's full list must not contain A's customer id
        assert data["customer_id"] not in _row_ids(payload, "customers")

        # Sanity: A still sees its own customer
        resp = httpx.get(
            f"{SERVER_URL}/api/customers",
            params={"search": data["customer_email"]},
            headers=test_admin_headers,
            timeout=10,
        )
        payload = assert_ok(resp)
        assert data["customer_id"] in _row_ids(payload, "customers")

    def test_ticket_list_does_not_leak(
        self, isolation_data: dict, test_admin_headers: dict, second_tenant_headers: dict
    ):
        data = isolation_data
        resp = httpx.get(f"{SERVER_URL}/api/tickets", headers=second_tenant_headers, timeout=10)
        payload = assert_ok(resp)
        assert data["ticket_id"] not in _row_ids(payload, "tickets"), (
            f"Tenant B saw tenant A's ticket: {payload.get('tickets', [])}"
        )
        # Sanity: A still sees its own ticket
        resp = httpx.get(f"{SERVER_URL}/api/tickets", headers=test_admin_headers, timeout=10)
        payload = assert_ok(resp)
        assert data["ticket_id"] in _row_ids(payload, "tickets")

    def test_invoice_list_does_not_leak(
        self, isolation_data: dict, test_admin_headers: dict, second_tenant_headers: dict
    ):
        data = isolation_data
        resp = httpx.get(f"{SERVER_URL}/api/invoices", headers=second_tenant_headers, timeout=10)
        payload = assert_ok(resp)
        assert data["invoice_id"] not in _row_ids(payload, "invoices"), (
            f"Tenant B saw tenant A's invoice: {payload.get('invoices', [])}"
        )
        # Sanity: A still sees its own invoice
        resp = httpx.get(f"{SERVER_URL}/api/invoices", headers=test_admin_headers, timeout=10)
        payload = assert_ok(resp)
        assert data["invoice_id"] in _row_ids(payload, "invoices")


# ── 2. Cross-tenant direct entity fetch by ID ───────────────────────


class TestCrossTenantFetchById:
    """Direct fetch of a foreign entity ID must look like 'not found' (404)."""

    def test_ticket_fetch_by_id_returns_404(
        self, isolation_data: dict, test_admin_headers: dict, second_tenant_headers: dict
    ):
        data = isolation_data
        resp = httpx.get(
            f"{SERVER_URL}/api/tickets/{data['ticket_id']}",
            headers=second_tenant_headers,
            timeout=10,
        )
        assert resp.status_code == 404, (
            f"Expected 404 fetching foreign ticket, got {resp.status_code}: {resp.text[:200]}"
        )
        # Sanity: A can fetch its own ticket
        resp = httpx.get(
            f"{SERVER_URL}/api/tickets/{data['ticket_id']}",
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_ticket_subresources_fetch_returns_404(
        self, isolation_data: dict, second_tenant_headers: dict
    ):
        data = isolation_data
        for path in (
            f"/api/tickets/{data['ticket_id']}/notes",
            f"/api/tickets/{data['ticket_id']}/checklist",
        ):
            resp = httpx.get(f"{SERVER_URL}{path}", headers=second_tenant_headers, timeout=10)
            assert resp.status_code == 404, (
                f"Expected 404 fetching {path}, got {resp.status_code}: {resp.text[:200]}"
            )

    def test_invoice_subresources_fetch_returns_404(
        self, isolation_data: dict, second_tenant_headers: dict
    ):
        data = isolation_data
        for path in (
            f"/api/invoices/{data['invoice_id']}/line-items",
            f"/api/invoices/{data['invoice_id']}/pdf",
        ):
            resp = httpx.get(f"{SERVER_URL}{path}", headers=second_tenant_headers, timeout=10)
            assert resp.status_code == 404, (
                f"Expected 404 fetching {path}, got {resp.status_code}: {resp.text[:200]}"
            )


# ── 3. Cross-tenant mutation via known ID ───────────────────────────


class TestCrossTenantMutationRejected:
    """Mutations targeting a foreign entity ID must be rejected (404)."""

    def test_customer_mutations_rejected(
        self, isolation_data: dict, test_admin_headers: dict, second_tenant_headers: dict
    ):
        data = isolation_data
        cid = data["customer_id"]

        # PUT (update) from tenant B
        resp = httpx.put(
            f"{SERVER_URL}/api/customers/{cid}",
            json={
                "first_name": "HACKED",
                "last_name": "HACKED",
                "email": "hacked@example.com",
                "phone": "000",
            },
            headers=second_tenant_headers,
            timeout=10,
        )
        assert resp.status_code == 404, (
            f"Expected 404 updating foreign customer, got {resp.status_code}: {resp.text[:200]}"
        )

        # DELETE from tenant B
        resp = httpx.delete(
            f"{SERVER_URL}/api/customers/{cid}", headers=second_tenant_headers, timeout=10
        )
        assert resp.status_code == 404, (
            f"Expected 404 deleting foreign customer, got {resp.status_code}: {resp.text[:200]}"
        )

        # Integrity: A's customer is completely untouched
        resp = httpx.get(
            f"{SERVER_URL}/api/customers",
            params={"search": data["customer_email"]},
            headers=test_admin_headers,
            timeout=10,
        )
        payload = assert_ok(resp)
        found = next((c for c in payload["customers"] if c["id"] == cid), None)
        assert found is not None, "Customer A vanished after B's mutations"
        assert found["first_name"] == data["customer_first_name"], (
            f"Customer A was modified by tenant B: {found}"
        )
        assert found["email"] == data["customer_email"]

    def test_ticket_mutations_rejected(
        self, isolation_data: dict, test_admin_headers: dict, second_tenant_headers: dict
    ):
        data = isolation_data
        tid = data["ticket_id"]

        # Status change from tenant B
        resp = httpx.put(
            f"{SERVER_URL}/api/tickets/{tid}/status",
            json={"status": "resolved"},
            headers=second_tenant_headers,
            timeout=10,
        )
        assert resp.status_code == 404, (
            f"Expected 404 updating foreign ticket status, got {resp.status_code}: {resp.text[:200]}"
        )

        # Note injection from tenant B
        resp = httpx.post(
            f"{SERVER_URL}/api/tickets/{tid}/notes",
            json={"author": "attacker", "content": "injected note", "internal": False},
            headers=second_tenant_headers,
            timeout=10,
        )
        assert resp.status_code == 404, (
            f"Expected 404 adding note to foreign ticket, got {resp.status_code}: {resp.text[:200]}"
        )

        # Delete from tenant B
        resp = httpx.delete(
            f"{SERVER_URL}/api/tickets/{tid}", headers=second_tenant_headers, timeout=10
        )
        assert resp.status_code == 404, (
            f"Expected 404 deleting foreign ticket, got {resp.status_code}: {resp.text[:200]}"
        )

        # Integrity: status unchanged, no foreign note attached
        tdata = httpx.get(
            f"{SERVER_URL}/api/tickets/{tid}", headers=test_admin_headers, timeout=10
        ).json()["ticket"]
        assert tdata["status"] == data["ticket_status"], (
            f"Ticket A status was changed by tenant B: {tdata['status']}"
        )
        notes = httpx.get(
            f"{SERVER_URL}/api/tickets/{tid}/notes", headers=test_admin_headers, timeout=10
        ).json()["notes"]
        assert all("injected note" not in (n.get("content") or "") for n in notes), (
            f"Tenant B injected a note into ticket A: {notes}"
        )

    def test_invoice_mutations_rejected(
        self, isolation_data: dict, test_admin_headers: dict, second_tenant_headers: dict
    ):
        data = isolation_data
        iid = data["invoice_id"]

        # Status change from tenant B
        resp = httpx.put(
            f"{SERVER_URL}/api/invoices/{iid}/status",
            json={"status": "paid"},
            headers=second_tenant_headers,
            timeout=10,
        )
        assert resp.status_code == 404, (
            f"Expected 404 updating foreign invoice status, got {resp.status_code}: {resp.text[:200]}"
        )

        # Line-item injection from tenant B
        resp = httpx.post(
            f"{SERVER_URL}/api/invoices/{iid}/line-items",
            json={
                "item_type": "service",
                "description": "injected item",
                "quantity": 1,
                "unit_price": 999,
            },
            headers=second_tenant_headers,
            timeout=10,
        )
        assert resp.status_code == 404, (
            f"Expected 404 adding line item to foreign invoice, got {resp.status_code}: {resp.text[:200]}"
        )

        # Delete from tenant B
        resp = httpx.delete(
            f"{SERVER_URL}/api/invoices/{iid}", headers=second_tenant_headers, timeout=10
        )
        assert resp.status_code == 404, (
            f"Expected 404 deleting foreign invoice, got {resp.status_code}: {resp.text[:200]}"
        )

        # Integrity: status unchanged, no foreign line item attached
        assert _get_invoice_status(test_admin_headers, iid) == data["invoice_status"], (
            "Invoice A status was changed by tenant B"
        )
        items = httpx.get(
            f"{SERVER_URL}/api/invoices/{iid}/line-items",
            headers=test_admin_headers,
            timeout=10,
        ).json()["line_items"]
        assert all("injected item" not in (i.get("description") or "") for i in items), (
            f"Tenant B injected a line item into invoice A: {items}"
        )


# ── 4. Concurrent list requests ─────────────────────────────────────


class TestConcurrentTenantRequests:
    """A burst of parallel list requests must leak nothing and never 5xx."""

    async def test_concurrent_list_requests_no_leakage(
        self, isolation_data: dict, test_admin_headers: dict, second_tenant_headers: dict
    ):
        data = isolation_data
        a_headers = {"Authorization": test_admin_headers["Authorization"]}
        b_headers = {"Authorization": second_tenant_headers["Authorization"]}

        # Each origin rotates through the three list endpoints.
        # 5 requests per tenant = 10 parallel requests total.
        a_paths = [
            f"/api/customers?search={data['customer_email']}",
            "/api/tickets",
            "/api/invoices",
        ]
        b_paths = [
            f"/api/customers?search={data['customer_email']}",
            "/api/tickets",
            "/api/invoices",
        ]
        plan = [(a_paths[i % 3], a_headers, "A") for i in range(5)] + [
            (b_paths[i % 3], b_headers, "B") for i in range(5)
        ]

        async with httpx.AsyncClient(base_url=SERVER_URL, timeout=15) as client:

            async def fetch(path: str, headers: dict, origin: str):
                resp = await client.get(path, headers=headers)
                return origin, path, resp.status_code, resp.json()

            results = await asyncio.gather(*[fetch(p, h, o) for p, h, o in plan])
            assert len(results) == 10

        for origin, path, status, payload in results:
            # Never a server error under concurrency
            assert status == 200, (
                f"Concurrent request failed: origin={origin} path={path} "
                f"status={status} body={str(payload)[:200]}"
            )
            assert status < 500

            if origin == "B":
                # B must never receive any of A's entities
                if "customers" in payload:
                    for c in payload["customers"]:
                        assert c["id"] != data["customer_id"], (
                            "Tenant B received tenant A's customer under concurrency"
                        )
                        assert c.get("email") != data["customer_email"]
                if "tickets" in payload:
                    assert data["ticket_id"] not in _row_ids(payload, "tickets"), (
                        "Tenant B received tenant A's ticket under concurrency"
                    )
                if "invoices" in payload:
                    assert data["invoice_id"] not in _row_ids(payload, "invoices"), (
                        "Tenant B received tenant A's invoice under concurrency"
                    )
            else:
                # Sanity: A must still see its own entities (requests work)
                if "customers" in payload:
                    assert data["customer_id"] in _row_ids(payload, "customers")
                if "tickets" in payload:
                    assert data["ticket_id"] in _row_ids(payload, "tickets")
                if "invoices" in payload:
                    assert data["invoice_id"] in _row_ids(payload, "invoices")

        # B's own customer must still be visible to B (B's data intact,
        # and B's searches for A's email must stay empty after the burst)
        resp = httpx.get(
            f"{SERVER_URL}/api/customers",
            params={"search": data["b_customer_email"]},
            headers=second_tenant_headers,
            timeout=10,
        )
        payload = assert_ok(resp)
        assert data["b_customer_id"] in _row_ids(payload, "customers")

        resp = httpx.get(
            f"{SERVER_URL}/api/customers",
            params={"search": data["customer_email"]},
            headers=second_tenant_headers,
            timeout=10,
        )
        payload = assert_ok(resp)
        assert payload.get("customers", []) == []


# ── 4. Cross-tenant mutations on remaining guarded entities ────────


class TestAdditionalEntityIsolation:
    """Every entity guarded by _require_owned must reject cross-tenant mutation.

    Covers: purchase orders, estimates, appointments, tax rates, payment
    methods, webhook subscriptions, checklist templates, custom field
    definitions, scheduled reports, recurring invoice rules.
    """

    def _create_a_entity(self, path: str, payload: dict, headers: dict) -> str:
        resp = httpx.post(f"{SERVER_URL}{path}", json=payload, headers=headers, timeout=10)
        assert resp.status_code == 200, f"Create {path} failed: {resp.text[:300]}"
        data = resp.json()
        # Entities return either an id in the body or nothing (look up via list)
        if isinstance(data, dict) and data.get("id"):
            return str(data["id"])
        raise AssertionError(f"No id returned from {path}: {data}")

    def test_purchase_order_mutations_rejected(
        self, isolation_data: dict, test_admin_headers: dict, second_tenant_headers: dict
    ):
        data = isolation_data
        # Create a PO in tenant A
        resp = httpx.post(
            f"{SERVER_URL}/api/purchase-orders",
            json={"vendor_name": "Isolation Vendor", "notes": "", "currency": "USD"},
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 200
        rows = _stdb_sql("SELECT * FROM purchase_order")
        po_id = rows[0]["rows"][-1][0]

        # Tenant B: delete, approve, receive — all must 404
        for method, path, payload in (
            ("delete", f"/api/purchase-orders/{po_id}", None),
            ("post", f"/api/purchase-orders/{po_id}/approve", {"user_id": "u_x"}),
            ("post", f"/api/purchase-orders/{po_id}/receive", {"received_quantity": 0, "items": [{"id": "li_x", "received_quantity": 0}]}),
            ("put", f"/api/purchase-orders/{po_id}/status", {"status": "cancelled"}),
        ):
            resp = httpx.request(
                method.upper(),
                f"{SERVER_URL}{path}",
                json=payload,
                headers=second_tenant_headers,
                timeout=10,
            )
            assert resp.status_code == 404, (
                f"Expected 404 {method} {path}, got {resp.status_code}: {resp.text[:200]}"
            )

    def test_estimate_mutations_rejected(
        self, isolation_data: dict, test_admin_headers: dict, second_tenant_headers: dict
    ):
        data = isolation_data
        resp = httpx.post(
            f"{SERVER_URL}/api/estimates",
            json={
                "customer_id": data["customer_id"],
                "ticket_id": "",
                "notes": "isolation estimate",
                "expires_at": 0,
                "currency": "USD",
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 200
        rows = _stdb_sql("SELECT * FROM estimates")
        est_id = rows[0]["rows"][-1][0]

        for method, path, payload in (
            ("delete", f"/api/estimates/{est_id}", None),
            ("put", f"/api/estimates/{est_id}/status", {"status": "approved"}),
            ("post", f"/api/estimates/{est_id}/line-items", {"item_type": "service", "description": "x", "quantity": 1, "unit_price": 1}),
        ):
            resp = httpx.request(
                method.upper(), f"{SERVER_URL}{path}", json=payload,
                headers=second_tenant_headers, timeout=10,
            )
            assert resp.status_code == 404, (
                f"Expected 404 {method} {path}, got {resp.status_code}: {resp.text[:200]}"
            )

    def test_appointment_mutations_rejected(
        self, isolation_data: dict, test_admin_headers: dict, second_tenant_headers: dict
    ):
        data = isolation_data
        resp = httpx.post(
            f"{SERVER_URL}/api/appointments",
            json={
                "customer_id": data["customer_id"],
                "title": "Isolation appt",
                "description": "x",
                "start_time": 1783000000000,
                "end_time": 1783003600000,
                "all_day": False,
                "series_id": "",
                "recurrence_rule": "",
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 200
        rows = _stdb_sql("SELECT * FROM appointment")
        appt_id = rows[0]["rows"][-1][0]

        for method, path, payload in (
            ("delete", f"/api/appointments/{appt_id}", None),
            ("put", f"/api/appointments/{appt_id}/status", {"status": "cancelled"}),
            ("put", f"/api/appointments/{appt_id}/recurrence", {"recurrence_rule": "monthly"}),
        ):
            resp = httpx.request(
                method.upper(), f"{SERVER_URL}{path}", json=payload,
                headers=second_tenant_headers, timeout=10,
            )
            assert resp.status_code == 404, (
                f"Expected 404 {method} {path}, got {resp.status_code}: {resp.text[:200]}"
            )

    def test_tax_rate_and_schedule_mutations_rejected(
        self, isolation_data: dict, test_admin_headers: dict, second_tenant_headers: dict
    ):
        data = isolation_data
        resp = httpx.post(
            f"{SERVER_URL}/api/tax-rates",
            json={"name": "Isolation Tax", "rate": 8.5, "is_default": False},
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 200
        rows = _stdb_sql("SELECT * FROM tax_rates")
        tax_id = rows[0]["rows"][-1][0]

        resp = httpx.delete(f"{SERVER_URL}/api/tax-rates/{tax_id}", headers=second_tenant_headers, timeout=10)
        assert resp.status_code == 404, (
            f"Expected 404 deleting foreign tax rate, got {resp.status_code}: {resp.text[:200]}"
        )

        # Scheduled report: create in A, run-now from B must 404
        resp = httpx.post(
            f"{SERVER_URL}/api/report-schedules",
            json={
                "name": "Isolation Report",
                "report_type": "revenue",
                "schedule_frequency": "daily",
                "schedule_config": {"hour": 8, "minute": 0},
                "recipients": [data["customer_email"]],
                "filters": {},
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 200
        rows = _stdb_sql("SELECT * FROM scheduled_reports")
        sched_id = rows[0]["rows"][-1][0]

        resp = httpx.post(
            f"{SERVER_URL}/api/report-schedules/{sched_id}/run-now",
            headers=second_tenant_headers,
            timeout=10,
        )
        assert resp.status_code == 404, (
            f"Expected 404 running foreign schedule, got {resp.status_code}: {resp.text[:200]}"
        )

        resp = httpx.delete(f"{SERVER_URL}/api/report-schedules/{sched_id}", headers=second_tenant_headers, timeout=10)
        assert resp.status_code == 404, (
            f"Expected 404 deleting foreign schedule, got {resp.status_code}: {resp.text[:200]}"
        )
