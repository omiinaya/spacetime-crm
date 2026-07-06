"""Ticket, invoice, and payment flow integration tests."""
import pytest
import httpx
from .conftest import SERVER_URL, assert_ok, create_customer, unique_suffix


def _reset_sla_targets(auth_headers: dict) -> None:
    """Reset SLA targets back to defaults for test isolation."""
    defaults = {"urgent": 4, "high": 24, "medium": 72, "low": 120}
    httpx.post(
        f"{SERVER_URL}/api/tickets/sla-settings",
        json={"targets": defaults},
        headers=auth_headers, timeout=10,
    )


def _create_ticket(auth_headers: dict, cid: str, title: str = "Broken screen") -> str:
    """Create a ticket and return its ID by reading back the list."""
    resp = httpx.post(
        f"{SERVER_URL}/api/tickets",
        json={"customer_id": cid, "title": title, "description": "Test ticket", "priority": "high"},
        headers=auth_headers, timeout=10,
    )
    assert_ok(resp)
    # List tickets and find the one we just created
    r = httpx.get(f"{SERVER_URL}/api/tickets", params={"limit": 20}, headers=auth_headers, timeout=10)
    tickets = r.json().get("tickets", [])
    # Return the most recent ticket matching our title
    for t in reversed(tickets):
        if t.get("title") == title:
            return t["id"]
    return tickets[0]["id"] if tickets else ""


class TestTicketFlow:
    """Full ticket lifecycle."""

    def test_create_ticket(self, auth_headers: dict):
        """Create a ticket with linked customer."""
        customer = create_customer(auth_headers, first_name="Ticket", last_name="Flow")
        cid = customer.get("id")
        assert cid

        resp = httpx.post(
            f"{SERVER_URL}/api/tickets",
            json={
                "customer_id": cid,
                "title": "Broken screen",
                "description": "Cracked glass",
                "device_type": "iPhone",
                "device_model": "15",
                "device_serial": f"SN-{unique_suffix()}",
                "priority": "high",
            },
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert data.get("ok") is True

    def test_list_tickets(self, auth_headers: dict):
        """List tickets returns results."""
        resp = httpx.get(
            f"{SERVER_URL}/api/tickets",
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert "tickets" in data

    def test_update_ticket_status(self, auth_headers: dict):
        """Update ticket status -- creates own ticket."""
        customer = create_customer(auth_headers, first_name="Status", last_name="Update")
        tid = _create_ticket(auth_headers, customer["id"], "Status update ticket")
        assert tid, "No ticket created"

        resp = httpx.put(
            f"{SERVER_URL}/api/tickets/{tid}/status",
            json={"status": "in_progress"},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_add_ticket_note(self, auth_headers: dict):
        """Add a note to a ticket -- creates own ticket."""
        customer = create_customer(auth_headers, first_name="Note", last_name="Test")
        tid = _create_ticket(auth_headers, customer["id"], "Note test ticket")
        assert tid, "No ticket created"

        resp = httpx.post(
            f"{SERVER_URL}/api/tickets/{tid}/notes",
            json={"author": "Test Tech", "content": "Inspected device", "internal": False},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

        # Verify note was created
        notes_resp = httpx.get(
            f"{SERVER_URL}/api/tickets/{tid}/notes",
            headers=auth_headers, timeout=10,
        )
        notes_data = assert_ok(notes_resp)
        notes = notes_data.get("notes", [])
        assert len(notes) > 0


class TestInvoiceFlow:
    """Invoice creation and management."""

    def test_create_invoice(self, auth_headers: dict):
        """Create a basic invoice."""
        customer = create_customer(auth_headers, first_name="Invoice", last_name="Test")
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
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert data.get("ok") is True

    def test_list_invoices(self, auth_headers: dict):
        """List invoices returns results."""
        resp = httpx.get(
            f"{SERVER_URL}/api/invoices",
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert "invoices" in data


class TestProductFlow:
    """Product/inventory CRUD."""

    def test_create_product(self, auth_headers: dict):
        """Create a product."""
        sku = f"SCR-{unique_suffix()}"
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
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert data.get("ok") is True

    def test_list_products(self, auth_headers: dict):
        """List products."""
        resp = httpx.get(
            f"{SERVER_URL}/api/products",
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert "products" in data


class TestTicketSLA:
    """SLA breach detection."""

    def test_sla_breach_list(self, auth_headers: dict):
        """SLA breaches endpoint returns a list with count."""
        customer = create_customer(auth_headers, first_name="SLA", last_name="Test")
        httpx.post(
            f"{SERVER_URL}/api/tickets",
            json={"customer_id": customer["id"], "title": "SLA breach test", "priority": "urgent"},
            headers=auth_headers, timeout=10,
        )
        resp = httpx.get(f"{SERVER_URL}/api/tickets/sla-breached", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "breaches" in data
        assert "count" in data
        # The just-created ticket may or may not be breached depending on elapsed time
        assert isinstance(data["count"], int)

    def test_sla_targets(self, auth_headers: dict):
        """SLA targets endpoint returns priority thresholds."""
        # Reset to defaults first (in case previous test changed them)
        _reset_sla_targets(auth_headers)
        resp = httpx.get(f"{SERVER_URL}/api/tickets/sla-targets", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "targets" in data
        targets = data["targets"]
        assert "urgent" in targets
        assert targets["urgent"] == 4
        assert targets["high"] == 24
        assert targets["medium"] == 72
        assert targets["low"] == 120

    def test_sla_breach_unauthed(self, client: httpx.Client):
        """SLA endpoints require auth."""
        resp = client.get("/api/tickets/sla-breached", timeout=10)
        assert resp.status_code in (401, 403)

    def test_sla_settings_get(self, auth_headers: dict):
        """GET sla-settings returns current config."""
        _reset_sla_targets(auth_headers)
        resp = httpx.get(f"{SERVER_URL}/api/tickets/sla-settings", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "targets" in data
        assert "updated_at" in data
        assert data["targets"]["urgent"] == 4

    def test_sla_settings_save(self, auth_headers: dict):
        """POST sla-settings saves and returns new config."""
        custom = {"urgent": 1, "high": 8, "medium": 24, "low": 48}
        resp = httpx.post(
            f"{SERVER_URL}/api/tickets/sla-settings",
            json={"targets": custom},
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert data["ok"] is True
        assert data["targets"]["urgent"] == 1.0
        # Verify persistence
        resp2 = httpx.get(f"{SERVER_URL}/api/tickets/sla-targets", headers=auth_headers, timeout=10)
        data2 = assert_ok(resp2)
        assert data2["targets"]["urgent"] == 1.0
        # Reset for other tests
        _reset_sla_targets(auth_headers)

    def test_sla_settings_validation(self, auth_headers: dict):
        """POST sla-settings validates inputs."""
        # Missing key
        resp = httpx.post(
            f"{SERVER_URL}/api/tickets/sla-settings",
            json={"targets": {"urgent": 4, "high": 24, "medium": 72}},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 400
        # Non-positive value
        resp = httpx.post(
            f"{SERVER_URL}/api/tickets/sla-settings",
            json={"targets": {"urgent": 0, "high": 24, "medium": 72, "low": 120}},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 400
        # Exceeds max
        resp = httpx.post(
            f"{SERVER_URL}/api/tickets/sla-settings",
            json={"targets": {"urgent": 9000, "high": 24, "medium": 72, "low": 120}},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 400
        assert "exceeds max" in resp.text

    def test_sla_settings_auth_guard(self, client: httpx.Client):
        """sla-settings endpoints require auth."""
        resp = client.get("/api/tickets/sla-settings", timeout=10)
        assert resp.status_code in (401, 403)
        resp = client.post("/api/tickets/sla-settings", json={"targets": {"urgent": 4, "high": 24, "medium": 72, "low": 120}}, timeout=10)
        assert resp.status_code in (401, 403)
