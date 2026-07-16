"""Ticket, invoice, and payment flow integration tests.

Each test method creates its own data for full STDB state isolation.
Helpers use unique identifiers + STDB SQL lookups so tests are safe to
run in parallel or in any order.
"""

import httpx

from .conftest import (
    SERVER_URL,
    _stdb_sql,
    _track_entity,
    assert_ok,
    create_customer,
    reset_sla_targets,
    restore_sla_targets,
    save_sla_targets,
    unique_suffix,
)


def _create_ticket(test_admin_headers: dict, session_suffix: str = "", suffix: str = "", **overrides) -> str:
    """Create a customer + ticket and return the ticket ID.

    Uses a unique serial number and direct STDB SQL to find the ticket,
    ensuring full isolation from other test data.
    session_suffix ensures cleanup by suffix works across sessions.
    """
    suf = suffix or unique_suffix()
    email = f"tkt-cust-{session_suffix}-{suf}@example.com"
    cust = create_customer(
        test_admin_headers,
        session_suffix=session_suffix,
        first_name="Ticket",
        last_name=f"Test{suf}",
        email=email,
    )
    cid = cust.get("id")
    assert cid, f"Failed to create customer: {cust}"

    device_serial = overrides.get("device_serial", f"SN-{session_suffix}-{suf}")
    resp = httpx.post(
        f"{SERVER_URL}/api/tickets",
        json={
            "customer_id": cid,
            "title": overrides.get("title", "Test ticket"),
            "description": overrides.get("description", "Auto-generated"),
            "device_type": overrides.get("device_type", "Phone"),
            "device_model": overrides.get("device_model", "X"),
            "device_serial": device_serial,
            "priority": overrides.get("priority", "medium"),
        },
        headers=test_admin_headers,
        timeout=10,
    )
    assert_ok(resp)

    # Look up ticket by unique device_serial via STDB SQL
    rows = _stdb_sql(f"SELECT * FROM ticket WHERE device_serial = '{device_serial}'")
    assert len(rows) == 1, f"Expected 1 ticket with serial {device_serial}, got {len(rows)}"
    tid = rows[0]["id"]
    _track_entity("ticket", tid)
    return tid


class TestTicketFlow:
    """Full ticket lifecycle."""

    def test_create_ticket(self, test_admin_headers: dict, session_suffix: str) -> None:
        """Create a ticket with linked customer."""
        tid = _create_ticket(test_admin_headers, session_suffix, "create")
        assert tid, "Expected a ticket ID"
        assert tid.startswith("tkt_"), f"Unexpected ticket ID format: {tid}"

    def test_list_tickets(self, test_admin_headers: dict) -> None:
        """List tickets returns results."""
        resp = httpx.get(
            f"{SERVER_URL}/api/tickets",
            headers=test_admin_headers,
            timeout=10,
        )
        data = assert_ok(resp)
        assert "tickets" in data

    def test_update_ticket_status(self, test_admin_headers: dict, session_suffix: str) -> None:
        """Update ticket status using own ticket data."""
        tid = _create_ticket(test_admin_headers, session_suffix, "updstatus", title="Status Update Test")
        resp = httpx.put(
            f"{SERVER_URL}/api/tickets/{tid}/status",
            json={"status": "in_progress"},
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_add_ticket_note(self, test_admin_headers: dict, session_suffix: str) -> None:
        """Add a note to a ticket using own ticket data."""
        tid = _create_ticket(test_admin_headers, session_suffix, "note", title="Note Test")
        resp = httpx.post(
            f"{SERVER_URL}/api/tickets/{tid}/notes",
            json={"author": "Test Tech", "content": "Inspected device", "internal": False},
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

        # Verify note was created
        notes_resp = httpx.get(
            f"{SERVER_URL}/api/tickets/{tid}/notes",
            headers=test_admin_headers,
            timeout=10,
        )
        notes_data = assert_ok(notes_resp)
        notes = notes_data.get("notes", [])
        assert len(notes) > 0


class TestInvoiceFlow:
    """Invoice creation and management."""

    def test_create_invoice(self, test_admin_headers: dict, session_suffix: str) -> None:
        """Create a basic invoice."""
        customer = create_customer(
            test_admin_headers,
            session_suffix=session_suffix,
            first_name="Invoice",
            last_name="Test",
        )
        cid = customer.get("id")
        assert cid

        resp = httpx.post(
            f"{SERVER_URL}/api/invoices",
            json={
                "customer_id": cid,
                "ticket_id": "",
                "notes": "Test invoice",
                "terms": "Due on receipt",
                "due_date": 1893456000000,  # 2030-01-01
            },
            headers=test_admin_headers,
            timeout=10,
        )
        data = assert_ok(resp)
        assert data.get("ok") is True

    def test_list_invoices(self, test_admin_headers: dict) -> None:
        """List invoices returns results."""
        resp = httpx.get(
            f"{SERVER_URL}/api/invoices",
            headers=test_admin_headers,
            timeout=10,
        )
        data = assert_ok(resp)
        assert "invoices" in data


class TestProductFlow:
    """Product/inventory CRUD."""

    def test_create_product(self, test_admin_headers: dict, session_suffix: str) -> None:
        """Create a product."""
        sku = f"SCR-{session_suffix}-{unique_suffix()}"
        resp = httpx.post(
            f"{SERVER_URL}/api/products",
            json={
                "name": "Screen Protector",
                "sku": sku,
                "price": 19.99,
                "cost": 3.50,
                "quantity_on_hand": 100,
                "active": True,
            },
            headers=test_admin_headers,
            timeout=10,
        )
        data = assert_ok(resp)
        assert data.get("ok") is True

    def test_list_products(self, test_admin_headers: dict) -> None:
        """List products."""
        resp = httpx.get(
            f"{SERVER_URL}/api/products",
            headers=test_admin_headers,
            timeout=10,
        )
        data = assert_ok(resp)
        assert "products" in data


class TestTicketSLA:
    """SLA breach detection."""

    def test_sla_breach_list(self, test_admin_headers: dict, session_suffix: str) -> None:
        """SLA breaches endpoint returns a list with count."""
        saved = save_sla_targets(test_admin_headers)
        try:
            reset_sla_targets(test_admin_headers)
            _create_ticket(test_admin_headers, session_suffix, "sla", priority="urgent")
            resp = httpx.get(f"{SERVER_URL}/api/tickets/sla-breached", headers=test_admin_headers, timeout=10)
            data = assert_ok(resp)
            assert "breaches" in data
            assert "count" in data
            # The just-created ticket may or may not be breached depending on elapsed time
            assert isinstance(data["count"], int)
        finally:
            restore_sla_targets(test_admin_headers, saved)

    def test_sla_targets(self, test_admin_headers: dict) -> None:
        """SLA targets endpoint returns priority thresholds."""
        saved = save_sla_targets(test_admin_headers)
        try:
            reset_sla_targets(test_admin_headers)
            resp = httpx.get(f"{SERVER_URL}/api/tickets/sla-targets", headers=test_admin_headers, timeout=10)
            data = assert_ok(resp)
            assert "targets" in data
            targets = data["targets"]
            assert "urgent" in targets
            assert targets["urgent"] == 4
            assert targets["high"] == 24
            assert targets["medium"] == 72
            assert targets["low"] == 120
        finally:
            restore_sla_targets(test_admin_headers, saved)

    def test_sla_breach_unauthed(self, client: httpx.Client) -> None:
        """SLA endpoints require auth."""
        resp = client.get("/api/tickets/sla-breached", timeout=10)
        assert resp.status_code in (401, 403)

    def test_sla_settings_get(self, test_admin_headers: dict) -> None:
        """GET sla-settings returns current config."""
        saved = save_sla_targets(test_admin_headers)
        try:
            reset_sla_targets(test_admin_headers)
            resp = httpx.get(f"{SERVER_URL}/api/tickets/sla-settings", headers=test_admin_headers, timeout=10)
            data = assert_ok(resp)
            assert "targets" in data
            assert "updated_at" in data
            assert data["targets"]["urgent"] == 4
        finally:
            restore_sla_targets(test_admin_headers, saved)

    def test_sla_settings_save(self, test_admin_headers: dict) -> None:
        """POST sla-settings saves and returns new config. Always restores afterwards."""
        saved = save_sla_targets(test_admin_headers)
        try:
            custom = {"urgent": 1, "high": 8, "medium": 24, "low": 48}
            resp = httpx.post(
                f"{SERVER_URL}/api/tickets/sla-settings",
                json={"targets": custom},
                headers=test_admin_headers,
                timeout=10,
            )
            data = assert_ok(resp)
            assert data["ok"] is True
            assert data["targets"]["urgent"] == 1.0
            # Verify persistence
            resp2 = httpx.get(f"{SERVER_URL}/api/tickets/sla-targets", headers=test_admin_headers, timeout=10)
            data2 = assert_ok(resp2)
            assert data2["targets"]["urgent"] == 1.0
        finally:
            # Always restore original SLA settings for other tests
            restore_sla_targets(test_admin_headers, saved)

    def test_sla_settings_validation(self, test_admin_headers: dict) -> None:
        """POST sla-settings validates inputs."""
        saved = save_sla_targets(test_admin_headers)
        try:
            reset_sla_targets(test_admin_headers)
            # Missing key
            resp = httpx.post(
                f"{SERVER_URL}/api/tickets/sla-settings",
                json={"targets": {"urgent": 4, "high": 24, "medium": 72}},
                headers=test_admin_headers,
                timeout=10,
            )
            assert resp.status_code == 400
            # Non-positive value
            resp = httpx.post(
                f"{SERVER_URL}/api/tickets/sla-settings",
                json={"targets": {"urgent": 0, "high": 24, "medium": 72, "low": 120}},
                headers=test_admin_headers,
                timeout=10,
            )
            assert resp.status_code == 400
            # Exceeds max
            resp = httpx.post(
                f"{SERVER_URL}/api/tickets/sla-settings",
                json={"targets": {"urgent": 9000, "high": 24, "medium": 72, "low": 120}},
                headers=test_admin_headers,
                timeout=10,
            )
            assert resp.status_code == 400
            assert "exceeds max" in resp.text
        finally:
            restore_sla_targets(test_admin_headers, saved)

    def test_sla_settings_auth_guard(self, client: httpx.Client) -> None:
        """sla-settings endpoints require auth."""
        resp = client.get("/api/tickets/sla-settings", timeout=10)
        assert resp.status_code in (401, 403)
        resp = client.post(
            "/api/tickets/sla-settings",
            json={"targets": {"urgent": 4, "high": 24, "medium": 72, "low": 120}},
            timeout=10,
        )
        assert resp.status_code in (401, 403)


class TestTicketErrors:
    """Ticket endpoint error handling."""

    def test_create_missing_customer_id(self, test_admin_headers: dict) -> None:
        """Creating ticket without customer_id returns 422."""
        resp = httpx.post(
            f"{SERVER_URL}/api/tickets",
            json={"title": "No customer"},
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text[:200]}"

    def test_create_missing_title(self, test_admin_headers: dict) -> None:
        """Creating ticket without title returns 422."""
        resp = httpx.post(
            f"{SERVER_URL}/api/tickets",
            json={"customer_id": "test-cust"},
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text[:200]}"

    def test_add_note_missing_content(self, test_admin_headers: dict, session_suffix: str) -> None:
        """Adding note without content returns 422."""
        # Create a ticket first
        resp = httpx.post(
            f"{SERVER_URL}/api/tickets",
            json={"customer_id": "test-cust", "title": "Note test"},
            headers=test_admin_headers,
            timeout=10,
        )
        data = resp.json()
        ticket_id = data.get("id", "")
        if not ticket_id and "ticket" in data:
            ticket_id = data["ticket"].get("id", "")
        if ticket_id:
            _track_entity("ticket", ticket_id)
            resp2 = httpx.post(
                f"{SERVER_URL}/api/tickets/{ticket_id}/notes",
                json={"content": "", "internal": False},
                headers=test_admin_headers,
                timeout=10,
            )
            assert resp2.status_code == 422, f"Expected 422, got {resp2.status_code}: {resp2.text[:200]}"
