"""Customer portal integration tests — login, tickets, invoices, payments, appointments.

Each test creates its own data — no inter-test ordering dependencies.
All entities tracked for session cleanup.
Uses isolated tenant admin (not global admin) for all admin operations.
"""

import time

import bcrypt
import httpx
import pytest

from .conftest import SERVER_URL, _track_entity, assert_ok

_PORTAL_PW = "TestPortal123!"


@pytest.fixture(scope="session")
def portal_email(session_suffix: str) -> str:
    """Generate a unique portal customer email per session."""
    return f"portal-{session_suffix}@test.com"


@pytest.fixture(scope="session")
def portal_token(portal_email: str, test_admin_headers: dict) -> str:
    """Create portal customer, set password, log in, return token."""
    email = portal_email
    headers = test_admin_headers

    # Create customer
    create_resp = httpx.post(
        f"{SERVER_URL}/api/customers",
        json={
            "first_name": "Portal",
            "last_name": "User",
            "email": email,
            "phone": "555-0000",
        },
        headers=headers,
        timeout=10,
    )
    assert create_resp.status_code == 200, f"Customer create: {create_resp.text[:200]}"

    # Get STDB-assigned ID
    r2 = httpx.get(
        f"{SERVER_URL}/api/customers",
        params={"search": email},
        headers=headers,
        timeout=10,
    )
    items = r2.json().get("customers", [])
    assert items, f"Customer not found: {r2.text[:200]}"
    _track_entity("customer", items[0]["id"])

    # Set password via STDB reducer
    hashed = bcrypt.hashpw(_PORTAL_PW.encode(), bcrypt.gensalt()).decode()
    r = httpx.post(
        "http://localhost:3001/v1/database/spacetime-crm/call/set_customer_password",
        json=[items[0]["id"], hashed],
        timeout=10,
    )
    assert r.status_code < 300, f"Set password: {r.status_code} {r.text[:200]}"

    # Login
    resp = httpx.post(
        f"{SERVER_URL}/api/portal/login",
        json={"email": email, "password": _PORTAL_PW},
        timeout=10,
    )
    if resp.status_code == 429:
        time.sleep(6)
        resp = httpx.post(
            f"{SERVER_URL}/api/portal/login",
            json={"email": email, "password": _PORTAL_PW},
            timeout=10,
        )
    assert resp.status_code == 200, f"Portal login failed ({resp.status_code}): {resp.text[:200]}"
    return resp.json()["token"]


@pytest.fixture
def portal_headers(portal_token: str) -> dict:
    return {"Authorization": f"Bearer {portal_token}"}


@pytest.fixture
def portal_customer_id(portal_headers: dict) -> str:
    """Fetch the portal customer's ID for creating related entities."""
    resp = httpx.get(f"{SERVER_URL}/api/portal/me", headers=portal_headers, timeout=10)
    data = assert_ok(resp)
    return data["id"]


@pytest.fixture
def admin_headers(test_admin_headers: dict) -> dict:
    """Function-scoped admin auth headers using isolated tenant admin."""
    return test_admin_headers


def _create_portal_ticket(customer_id: str, admin_headers: dict, tag: str = "") -> str:
    """Create a ticket for the portal customer and return its ID."""
    title = f"Portal Test Ticket {tag}" if tag else "Portal Test Ticket"
    resp = httpx.post(
        f"{SERVER_URL}/api/tickets",
        json={
            "customer_id": customer_id,
            "title": title,
            "description": "Issue for portal testing",
        },
        headers=admin_headers,
        timeout=10,
    )
    data = assert_ok(resp)
    if "id" in data:
        tid = data["id"]
        _track_entity("ticket", tid)
        return tid
    return ""


def _create_portal_invoice(customer_id: str, admin_headers: dict, tag: str = "") -> str:
    """Create an invoice for the portal customer and return its ID."""
    notes = f"Portal invoice test {tag}" if tag else "Portal invoice test"
    resp = httpx.post(
        f"{SERVER_URL}/api/invoices",
        json={
            "customer_id": customer_id,
            "notes": notes,
            "due_date": 0,
        },
        headers=admin_headers,
        timeout=10,
    )
    data = assert_ok(resp)
    if "id" in data:
        inv_id = data["id"]
        _track_entity("invoice", inv_id)
        return inv_id
    return ""


class TestPortalAuth:
    """Portal login and profile."""

    def test_login_invalid(self, client: httpx.Client):
        resp = client.post(
            "/api/portal/login",
            json={"email": "nobody@test.com", "password": "wrong"},
            timeout=10,
        )
        assert resp.status_code == 401

    def test_login_missing_fields(self, client: httpx.Client):
        resp = client.post("/api/portal/login", json={}, timeout=10)
        assert resp.status_code == 422

    def test_portal_me(self, portal_headers: dict, portal_email: str):
        resp = httpx.get(f"{SERVER_URL}/api/portal/me", headers=portal_headers, timeout=10)
        data = assert_ok(resp)
        assert data["email"] == portal_email
        assert "first_name" in data
        assert "last_name" in data

    def test_portal_stats(self, portal_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/portal/stats", headers=portal_headers, timeout=10)
        data = assert_ok(resp)
        assert "total_tickets" in data
        assert "total_invoices" in data
        assert "balance_due" in data
        assert "upcoming_appointments" in data


class TestPortalTickets:
    """Customer ticket viewing and note adding — each test creates its own ticket."""

    def test_list_tickets(self, portal_headers: dict, portal_customer_id: str, admin_headers: dict):
        _create_portal_ticket(portal_customer_id, admin_headers, "list")
        resp = httpx.get(f"{SERVER_URL}/api/portal/tickets", headers=portal_headers, timeout=10)
        data = assert_ok(resp)
        assert "tickets" in data
        assert len(data["tickets"]) >= 1

    def test_ticket_detail(
        self, portal_headers: dict, portal_customer_id: str, admin_headers: dict
    ):
        tid = _create_portal_ticket(portal_customer_id, admin_headers, "detail")
        resp = httpx.get(
            f"{SERVER_URL}/api/portal/tickets/{tid}", headers=portal_headers, timeout=10
        )
        data = assert_ok(resp)
        assert "ticket" in data
        assert data["ticket"]["id"] == tid

    def test_ticket_nonexistent(self, portal_headers: dict):
        resp = httpx.get(
            f"{SERVER_URL}/api/portal/tickets/fake-id-99999",
            headers=portal_headers,
            timeout=10,
        )
        assert resp.status_code == 404

    def test_add_note(self, portal_headers: dict, portal_customer_id: str, admin_headers: dict):
        tid = _create_portal_ticket(portal_customer_id, admin_headers, "note")
        resp = httpx.post(
            f"{SERVER_URL}/api/portal/tickets/{tid}/notes",
            json={"content": "Customer update about my issue."},
            headers=portal_headers,
            timeout=10,
        )
        assert_ok(resp)


class TestPortalInvoices:
    """Customer invoice viewing — each test creates its own invoice."""

    def test_list_invoices(
        self, portal_headers: dict, portal_customer_id: str, admin_headers: dict
    ):
        _create_portal_invoice(portal_customer_id, admin_headers, "list")
        resp = httpx.get(f"{SERVER_URL}/api/portal/invoices", headers=portal_headers, timeout=10)
        data = assert_ok(resp)
        assert "invoices" in data
        assert len(data["invoices"]) >= 1

    def test_invoice_detail(
        self, portal_headers: dict, portal_customer_id: str, admin_headers: dict
    ):
        inv_id = _create_portal_invoice(portal_customer_id, admin_headers, "detail")
        resp = httpx.get(
            f"{SERVER_URL}/api/portal/invoices/{inv_id}",
            headers=portal_headers,
            timeout=10,
        )
        data = assert_ok(resp)
        assert "invoice" in data
        assert data["invoice"]["id"] == inv_id
        assert "line_items" in data["invoice"]
        assert "payments" in data["invoice"]

    def test_invoice_nonexistent(self, portal_headers: dict):
        resp = httpx.get(
            f"{SERVER_URL}/api/portal/invoices/fake-999",
            headers=portal_headers,
            timeout=10,
        )
        assert resp.status_code == 404


class TestPortalPayments:
    """Customer making payments and checking payment methods."""

    def test_make_payment(self, portal_headers: dict, portal_customer_id: str, admin_headers: dict):
        inv_id = _create_portal_invoice(portal_customer_id, admin_headers, "payment")
        # Add a line item so invoice has a balance
        httpx.post(
            f"{SERVER_URL}/api/invoices/{inv_id}/line-items",
            json={"description": "Service", "quantity": 1, "unit_price": 50},
            headers=admin_headers,
            timeout=10,
        )

        resp = httpx.post(
            f"{SERVER_URL}/api/portal/payments",
            json={
                "invoice_id": inv_id,
                "amount": 25,
                "method": "card",
                "reference": "PORTAL-TEST-1",
            },
            headers=portal_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_payment_invalid_amount(self, portal_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/portal/payments",
            json={"invoice_id": "fake", "amount": 0, "method": "card"},
            headers=portal_headers,
            timeout=10,
        )
        assert resp.status_code == 422

    def test_list_payment_methods(self, portal_headers: dict):
        resp = httpx.get(
            f"{SERVER_URL}/api/portal/payment-methods",
            headers=portal_headers,
            timeout=10,
        )
        data = assert_ok(resp)
        assert "payment_methods" in data


class TestPortalAppointments:
    """Customer appointment viewing."""

    def test_list_appointments(self, portal_headers: dict):
        resp = httpx.get(
            f"{SERVER_URL}/api/portal/appointments", headers=portal_headers, timeout=10
        )
        data = assert_ok(resp)
        assert "appointments" in data
        assert "upcoming" in data
        assert "past" in data


class TestPortalSettings:
    """Customer password change."""

    def test_set_password(self, portal_headers: dict, portal_email: str, portal_token: str):
        resp = httpx.post(
            f"{SERVER_URL}/api/portal/customer/set-password",
            json={"password": "NewPortalPass456!"},
            headers=portal_headers,
            timeout=10,
        )
        assert_ok(resp)

        resp = httpx.post(
            f"{SERVER_URL}/api/portal/login",
            json={"email": portal_email, "password": "NewPortalPass456!"},
            timeout=10,
        )
        assert resp.status_code == 200, f"New password login: {resp.text[:200]}"


class TestPortalErrors:
    """Portal auth enforcement."""

    def test_admin_token_rejected(self, test_admin_headers: dict):
        """Admin token (even from isolated tenant) should be rejected by portal endpoints."""
        headers = test_admin_headers
        resp = httpx.get(f"{SERVER_URL}/api/portal/me", headers=headers, timeout=10)
        assert resp.status_code == 401, f"Admin token should be rejected, got {resp.status_code}"

    def test_no_auth(self, client: httpx.Client):
        paths = [
            "/api/portal/me",
            "/api/portal/stats",
            "/api/portal/tickets",
            "/api/portal/invoices",
            "/api/portal/appointments",
            "/api/portal/payment-methods",
        ]
        for path in paths:
            resp = client.get(path, timeout=10)
            assert resp.status_code in (401, 403), f"{path} allowed unauthenticated"
