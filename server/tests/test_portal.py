"""Customer portal integration tests — login, tickets, invoices, payments, appointments."""
import bcrypt
import httpx
import pytest
import time
from .conftest import SERVER_URL, assert_ok, ADMIN_EMAIL, ADMIN_PW, unique_suffix

PORTAL_PW = "TestPortal123!"
PORTAL_EMAIL = f"portal-{unique_suffix()}@test.com"

# Track whether we've created the portal customer already (module-level flag)
_created = False
_cached_token = None
_cached_admin_token = None


def _admin_token() -> str:
    """Get an admin JWT (cached per session)."""
    global _cached_admin_token
    if _cached_admin_token:
        return _cached_admin_token
    resp = httpx.post(f"{SERVER_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW}, timeout=10)
    assert resp.status_code == 200, f"Admin login failed: {resp.text[:200]}"
    _cached_admin_token = resp.json()["token"]
    return _cached_admin_token


def _create_and_login() -> str:
    """Create the portal customer, set password, log in, return token."""
    global _created, _cached_token
    if _created and _cached_token:
        return _cached_token

    token = _admin_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Create customer
    create_resp = httpx.post(f"{SERVER_URL}/api/customers", json={
        "first_name": "Portal", "last_name": "User", "email": PORTAL_EMAIL, "phone": "555-0000",
    }, headers=headers, timeout=10)
    assert create_resp.status_code == 200, f"Customer create: {create_resp.text[:200]}"

    # Get STDB-assigned ID
    r2 = httpx.get(f"{SERVER_URL}/api/customers", params={"search": PORTAL_EMAIL}, headers=headers, timeout=10)
    items = r2.json().get("customers", [])
    assert items, f"Customer not found: {r2.text[:200]}"
    cid = items[0]["id"]

    # Set password via STDB reducer
    hashed = bcrypt.hashpw(PORTAL_PW.encode(), bcrypt.gensalt()).decode()
    r = httpx.post(
        "http://localhost:3001/v1/database/spacetime-crm/call/set_customer_password",
        json=[cid, hashed], timeout=10,
    )
    assert r.status_code < 300, f"Set password: {r.status_code} {r.text[:200]}"

    # Login
    resp = httpx.post(f"{SERVER_URL}/api/portal/login", json={"email": PORTAL_EMAIL, "password": PORTAL_PW}, timeout=10)
    if resp.status_code == 429:
        time.sleep(6)
        resp = httpx.post(f"{SERVER_URL}/api/portal/login", json={"email": PORTAL_EMAIL, "password": PORTAL_PW}, timeout=10)

    assert resp.status_code == 200, f"Portal login failed ({resp.status_code}): {resp.text[:200]}"
    _cached_token = resp.json()["token"]
    _created = True
    return _cached_token


@pytest.fixture(scope="session")
def portal_token() -> str:
    return _create_and_login()


@pytest.fixture
def portal_headers(portal_token: str) -> dict:
    return {"Authorization": f"Bearer {portal_token}"}


class TestPortalAuth:
    """Portal login and profile."""

    def test_login_invalid(self, client: httpx.Client):
        resp = client.post("/api/portal/login", json={"email": "nobody@test.com", "password": "wrong"}, timeout=10)
        assert resp.status_code == 401

    def test_login_missing_fields(self, client: httpx.Client):
        resp = client.post("/api/portal/login", json={}, timeout=10)
        assert resp.status_code == 422

    def test_portal_me(self, portal_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/portal/me", headers=portal_headers, timeout=10)
        data = assert_ok(resp)
        assert data["email"] == PORTAL_EMAIL
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
    """Customer ticket viewing and note adding."""

    def test_list_tickets(self, portal_headers: dict, portal_token: str):
        r = httpx.get(f"{SERVER_URL}/api/portal/me", headers=portal_headers, timeout=10)
        cid = r.json()["id"]
        token = _admin_token()
        admin_hdrs = {"Authorization": f"Bearer {token}"}

        httpx.post(f"{SERVER_URL}/api/tickets", json={
            "customer_id": cid, "title": "Portal Test Ticket", "description": "Issue for portal testing",
        }, headers=admin_hdrs, timeout=10)

        resp = httpx.get(f"{SERVER_URL}/api/portal/tickets", headers=portal_headers, timeout=10)
        data = assert_ok(resp)
        assert "tickets" in data
        assert len(data["tickets"]) >= 1

    def test_ticket_detail(self, portal_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/portal/tickets", headers=portal_headers, timeout=10)
        tickets = resp.json().get("tickets", [])
        if not tickets:
            pytest.skip("No tickets")
        tid = tickets[0]["id"]

        resp = httpx.get(f"{SERVER_URL}/api/portal/tickets/{tid}", headers=portal_headers, timeout=10)
        data = assert_ok(resp)
        assert "ticket" in data
        assert data["ticket"]["id"] == tid

    def test_ticket_nonexistent(self, portal_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/portal/tickets/fake-id-99999", headers=portal_headers, timeout=10)
        assert resp.status_code == 404

    def test_add_note(self, portal_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/portal/tickets", headers=portal_headers, timeout=10)
        tickets = resp.json().get("tickets", [])
        if not tickets:
            pytest.skip("No tickets")
        tid = tickets[0]["id"]

        resp = httpx.post(f"{SERVER_URL}/api/portal/tickets/{tid}/notes", json={"content": "Customer update about my issue."}, headers=portal_headers, timeout=10)
        assert_ok(resp)


class TestPortalInvoices:
    """Customer invoice viewing."""

    def test_list_invoices(self, portal_headers: dict):
        r = httpx.get(f"{SERVER_URL}/api/portal/me", headers=portal_headers, timeout=10)
        cid = r.json()["id"]
        token = _admin_token()
        admin_hdrs = {"Authorization": f"Bearer {token}"}

        httpx.post(f"{SERVER_URL}/api/invoices", json={"customer_id": cid, "notes": "Portal invoice test", "due_date": 0}, headers=admin_hdrs, timeout=10)

        resp = httpx.get(f"{SERVER_URL}/api/portal/invoices", headers=portal_headers, timeout=10)
        data = assert_ok(resp)
        assert "invoices" in data
        assert len(data["invoices"]) >= 1

    def test_invoice_detail(self, portal_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/portal/invoices", headers=portal_headers, timeout=10)
        invoices = resp.json().get("invoices", [])
        if not invoices:
            pytest.skip("No invoices")
        inv_id = invoices[0]["id"]

        resp = httpx.get(f"{SERVER_URL}/api/portal/invoices/{inv_id}", headers=portal_headers, timeout=10)
        data = assert_ok(resp)
        assert "invoice" in data
        assert data["invoice"]["id"] == inv_id
        assert "line_items" in data["invoice"]
        assert "payments" in data["invoice"]

    def test_invoice_nonexistent(self, portal_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/portal/invoices/fake-999", headers=portal_headers, timeout=10)
        assert resp.status_code == 404


class TestPortalPayments:
    """Customer making payments and checking payment methods."""

    def test_make_payment(self, portal_headers: dict):
        r = httpx.get(f"{SERVER_URL}/api/portal/me", headers=portal_headers, timeout=10)
        cid = r.json()["id"]
        token = _admin_token()
        admin_hdrs = {"Authorization": f"Bearer {token}"}

        httpx.post(f"{SERVER_URL}/api/invoices", json={"customer_id": cid, "notes": "Portal payment test", "due_date": 0}, headers=admin_hdrs, timeout=10)

        resp = httpx.get(f"{SERVER_URL}/api/portal/invoices", headers=portal_headers, timeout=10)
        invoices = resp.json().get("invoices", [])
        if not invoices:
            pytest.skip("No invoices")
        inv_id = invoices[0]["id"]

        httpx.post(f"{SERVER_URL}/api/invoices/{inv_id}/line-items", json={"description": "Service", "quantity": 1, "unit_price": 50}, headers=admin_hdrs, timeout=10)

        resp = httpx.post(f"{SERVER_URL}/api/portal/payments", json={"invoice_id": inv_id, "amount": 25, "method": "card", "reference": "PORTAL-TEST-1"}, headers=portal_headers, timeout=10)
        assert_ok(resp)

    def test_payment_invalid_amount(self, portal_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/portal/payments", json={"invoice_id": "fake", "amount": 0, "method": "card"}, headers=portal_headers, timeout=10)
        assert resp.status_code == 422

    def test_list_payment_methods(self, portal_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/portal/payment-methods", headers=portal_headers, timeout=10)
        data = assert_ok(resp)
        assert "payment_methods" in data


class TestPortalAppointments:
    """Customer appointment viewing."""

    def test_list_appointments(self, portal_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/portal/appointments", headers=portal_headers, timeout=10)
        data = assert_ok(resp)
        assert "appointments" in data
        assert "upcoming" in data
        assert "past" in data


class TestPortalSettings:
    """Customer password change."""

    def test_set_password(self, portal_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/portal/customer/set-password", json={"password": "NewPortalPass456!"}, headers=portal_headers, timeout=10)
        assert_ok(resp)

        resp = httpx.post(f"{SERVER_URL}/api/portal/login", json={"email": PORTAL_EMAIL, "password": "NewPortalPass456!"}, timeout=10)
        assert resp.status_code == 200, f"New password login: {resp.text[:200]}"


class TestPortalErrors:
    """Portal auth enforcement."""

    def test_admin_token_rejected(self):
        token = _admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        resp = httpx.get(f"{SERVER_URL}/api/portal/me", headers=headers, timeout=10)
        assert resp.status_code == 401, f"Admin token should be rejected, got {resp.status_code}"

    def test_no_auth(self, client: httpx.Client):
        paths = ["/api/portal/me", "/api/portal/stats", "/api/portal/tickets", "/api/portal/invoices", "/api/portal/appointments", "/api/portal/payment-methods"]
        for path in paths:
            resp = client.get(path, timeout=10)
            assert resp.status_code in (401, 403), f"{path} allowed unauthenticated"
