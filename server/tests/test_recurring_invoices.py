"""Recurring invoice rules CRUD + generate trigger tests."""
import httpx
import pytest
from .conftest import SERVER_URL, assert_ok, create_customer


def _customer_id(auth_headers: dict, suffix: str = "") -> str:
    """Create a customer and return ID."""
    c = create_customer(auth_headers, email=f"rec-{suffix or 'main'}@example.com")
    return c.get("id", "")


def _create_rule(auth_headers: dict, suffix: str = "") -> str:
    """Create a recurring invoice rule and return its ID."""
    cid = _customer_id(auth_headers, suffix)
    httpx.post(f"{SERVER_URL}/api/recurring-invoices", json={
        "customer_id": cid,
        "name": f"Monthly Service {suffix}",
        "frequency": "monthly",
        "interval_count": 1,
        "due_date_days": 30,
        "line_items": [{"description": "Service fee", "quantity": 1, "unit_price": 99.99}],
        "next_generation_date": int(__import__("time").time() * 1000) + 86400000,
    }, headers=auth_headers, timeout=10)

    resp = httpx.get(f"{SERVER_URL}/api/recurring-invoices", headers=auth_headers, timeout=10)
    rules = resp.json().get("rules", [])
    assert len(rules) >= 1
    return rules[0]["id"]


class TestRecurringInvoiceCRUD:
    """Recurring invoice rule create, list, update, delete."""

    def test_create(self, auth_headers: dict):
        cid = _customer_id(auth_headers, "cr-create")
        resp = httpx.post(f"{SERVER_URL}/api/recurring-invoices", json={
            "customer_id": cid,
            "name": "Weekly Cleaning",
            "frequency": "weekly",
            "interval_count": 1,
            "due_date_days": 14,
            "line_items": [{"description": "Cleaning service", "quantity": 1, "unit_price": 150}],
            "next_generation_date": int(__import__("time").time() * 1000) + 86400000,
        }, headers=auth_headers, timeout=10)
        assert_ok(resp)

    def test_create_invalid_frequency(self, auth_headers: dict):
        cid = _customer_id(auth_headers, "cr-badfreq")
        resp = httpx.post(f"{SERVER_URL}/api/recurring-invoices", json={
            "customer_id": cid, "name": "Bad", "frequency": "never",
            "interval_count": 1, "due_date_days": 30,
        }, headers=auth_headers, timeout=10)
        assert resp.status_code == 422

    def test_create_missing_customer(self, auth_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/recurring-invoices", json={
            "name": "No Cust", "frequency": "monthly",
            "interval_count": 1, "due_date_days": 30,
        }, headers=auth_headers, timeout=10)
        assert resp.status_code == 422

    def test_list(self, auth_headers: dict):
        _create_rule(auth_headers, "lst")
        resp = httpx.get(f"{SERVER_URL}/api/recurring-invoices", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "rules" in data
        # Verify customer name enrichment
        if data["rules"]:
            assert "customer_name" in data["rules"][0]

    def test_update(self, auth_headers: dict):
        rule_id = _create_rule(auth_headers, "upd")
        resp = httpx.put(f"{SERVER_URL}/api/recurring-invoices/{rule_id}", json={
            "name": "Updated Rule",
            "frequency": "monthly",
            "interval_count": 2,
            "due_date_days": 45,
            "line_items": [{"description": "Updated service", "quantity": 2, "unit_price": 75}],
            "next_generation_date": int(__import__("time").time() * 1000) + 172800000,
            "status": "active",
        }, headers=auth_headers, timeout=10)
        assert_ok(resp)

    def test_update_nonexistent(self, auth_headers: dict):
        resp = httpx.put(f"{SERVER_URL}/api/recurring-invoices/nonexistent-999", json={
            "name": "Nope", "frequency": "monthly", "interval_count": 1, "due_date_days": 30,
            "line_items": [], "next_generation_date": 0, "status": "active",
        }, headers=auth_headers, timeout=10)
        assert resp.status_code < 500

    def test_delete(self, auth_headers: dict):
        rule_id = _create_rule(auth_headers, "del")
        resp = httpx.delete(f"{SERVER_URL}/api/recurring-invoices/{rule_id}", headers=auth_headers, timeout=10)
        assert_ok(resp)

    def test_delete_nonexistent(self, auth_headers: dict):
        resp = httpx.delete(f"{SERVER_URL}/api/recurring-invoices/nonexistent-999", headers=auth_headers, timeout=10)
        assert resp.status_code < 500

    def test_generate(self, auth_headers: dict):
        """Generate endpoint should trigger the reducer without error."""
        resp = httpx.post(f"{SERVER_URL}/api/recurring-invoices/generate", headers=auth_headers, timeout=10)
        assert resp.status_code < 500

    def test_generate_with_data(self, auth_headers: dict):
        """Create a rule, then generate — should create invoices."""
        cid = _customer_id(auth_headers, "gen-data")
        # Set next gen to now
        now = int(__import__("time").time() * 1000)
        httpx.post(f"{SERVER_URL}/api/recurring-invoices", json={
            "customer_id": cid,
            "name": "Generate Test",
            "frequency": "monthly",
            "interval_count": 1,
            "due_date_days": 30,
            "line_items": [{"description": "Gen service", "quantity": 1, "unit_price": 50}],
            "next_generation_date": now - 1000,  # Past due
        }, headers=auth_headers, timeout=10)

        resp = httpx.post(f"{SERVER_URL}/api/recurring-invoices/generate", headers=auth_headers, timeout=10)
        assert_ok(resp)


class TestRecurringInvoiceErrors:
    """Auth enforcement."""

    def test_unauthorized_list(self, client: httpx.Client):
        resp = client.get("/api/recurring-invoices", timeout=10)
        assert resp.status_code in (401, 403)

    def test_unauthorized_create(self, client: httpx.Client):
        resp = client.post("/api/recurring-invoices", json={
            "customer_id": "x", "name": "X", "frequency": "monthly", "interval_count": 1, "due_date_days": 30,
        }, timeout=10)
        assert resp.status_code in (401, 403)

    def test_unauthorized_delete(self, client: httpx.Client):
        resp = client.delete("/api/recurring-invoices/fake-id", timeout=10)
        assert resp.status_code in (401, 403)
