"""Recurring invoice rules CRUD + generate trigger tests."""

import httpx
from .conftest import (
    SERVER_URL,
    assert_ok,
    create_customer,
    unique_suffix,
    _stdb_sql,
    _track_entity,
)


def _customer_id(
    test_admin_headers: dict, session_suffix: str = "", suffix: str = ""
) -> str:
    """Create a customer and return ID."""
    suf = suffix or unique_suffix()
    c = create_customer(
        test_admin_headers,
        session_suffix=session_suffix,
        email=f"rec-{session_suffix}-{suf}@example.com",
    )
    return c.get("id", "")


def _create_rule(
    test_admin_headers: dict, session_suffix: str = "", suffix: str = ""
) -> str:
    """Create a recurring invoice rule and return its ID.

    Uses unique name and STDB SQL lookup for isolation.
    """
    suf = suffix or unique_suffix()
    cid = _customer_id(test_admin_headers, suf)
    name = f"Monthly Service {session_suffix}-{suf}"
    httpx.post(
        f"{SERVER_URL}/api/recurring-invoices",
        json={
            "customer_id": cid,
            "name": name,
            "frequency": "monthly",
            "interval_count": 1,
            "due_date_days": 30,
            "line_items": [
                {"description": "Service fee", "quantity": 1, "unit_price": 99.99}
            ],
            "next_generation_date": int(__import__("time").time() * 1000) + 86400000,
        },
        headers=test_admin_headers,
        timeout=10,
    )

    result = _stdb_sql(f"SELECT id FROM recurring_invoice_rules WHERE name = '{name}'")
    assert len(result) == 1, f"Expected 1 table result for recurring rule '{name}'"
    table = result[0]
    assert table.get("rows") and len(table["rows"]) >= 1, (
        f"No rule found with name '{name}'"
    )
    rule_id = table["rows"][0][0]  # id is first (and only) column
    _track_entity("recurring_invoice_rule", rule_id)
    return rule_id


class TestRecurringInvoiceCRUD:
    """Recurring invoice rule create, list, update, delete."""

    def test_create(self, test_admin_headers: dict, session_suffix: str):
        cid = _customer_id(test_admin_headers, session_suffix, "cr-create")
        name = f"Weekly Cleaning {session_suffix}-{unique_suffix()}"
        resp = httpx.post(
            f"{SERVER_URL}/api/recurring-invoices",
            json={
                "customer_id": cid,
                "name": name,
                "frequency": "weekly",
                "interval_count": 1,
                "due_date_days": 14,
                "line_items": [
                    {
                        "description": "Cleaning service",
                        "quantity": 1,
                        "unit_price": 150,
                    }
                ],
                "next_generation_date": int(__import__("time").time() * 1000)
                + 86400000,
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_create_invalid_frequency(
        self, test_admin_headers: dict, session_suffix: str
    ):
        cid = _customer_id(test_admin_headers, session_suffix, "cr-badfreq")
        resp = httpx.post(
            f"{SERVER_URL}/api/recurring-invoices",
            json={
                "customer_id": cid,
                "name": "Bad",
                "frequency": "never",
                "interval_count": 1,
                "due_date_days": 30,
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 422

    def test_create_missing_customer(self, test_admin_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/recurring-invoices",
            json={
                "name": "No Cust",
                "frequency": "monthly",
                "interval_count": 1,
                "due_date_days": 30,
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 422

    def test_list(self, test_admin_headers: dict, session_suffix: str):
        _create_rule(test_admin_headers, session_suffix, "lst")
        resp = httpx.get(
            f"{SERVER_URL}/api/recurring-invoices",
            headers=test_admin_headers,
            timeout=10,
        )
        data = assert_ok(resp)
        assert "rules" in data
        # Verify customer name enrichment
        if data["rules"]:
            assert "customer_name" in data["rules"][0]

    def test_update(self, test_admin_headers: dict, session_suffix: str):
        rule_id = _create_rule(test_admin_headers, session_suffix, "upd")
        resp = httpx.put(
            f"{SERVER_URL}/api/recurring-invoices/{rule_id}",
            json={
                "name": "Updated Rule",
                "frequency": "monthly",
                "interval_count": 2,
                "due_date_days": 45,
                "line_items": [
                    {"description": "Updated service", "quantity": 2, "unit_price": 75}
                ],
                "next_generation_date": int(__import__("time").time() * 1000)
                + 172800000,
                "status": "active",
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_update_nonexistent(self, test_admin_headers: dict):
        resp = httpx.put(
            f"{SERVER_URL}/api/recurring-invoices/nonexistent-999",
            json={
                "name": "Nope",
                "frequency": "monthly",
                "interval_count": 1,
                "due_date_days": 30,
                "line_items": [],
                "next_generation_date": 0,
                "status": "active",
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code < 500

    def test_delete(self, test_admin_headers: dict, session_suffix: str):
        rule_id = _create_rule(test_admin_headers, session_suffix, "del")
        resp = httpx.delete(
            f"{SERVER_URL}/api/recurring-invoices/{rule_id}",
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_delete_nonexistent(self, test_admin_headers: dict):
        resp = httpx.delete(
            f"{SERVER_URL}/api/recurring-invoices/nonexistent-999",
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code < 500

    def test_generate(self, test_admin_headers: dict):
        """Generate endpoint should trigger the reducer without error."""
        resp = httpx.post(
            f"{SERVER_URL}/api/recurring-invoices/generate",
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code < 500

    def test_generate_with_data(self, test_admin_headers: dict, session_suffix: str):
        """Create a rule, then generate — should create invoices."""
        cid = _customer_id(test_admin_headers, session_suffix, "gen-data")
        name = f"Generate Test {session_suffix}-{unique_suffix()}"
        # Set next gen to now
        now = int(__import__("time").time() * 1000)
        httpx.post(
            f"{SERVER_URL}/api/recurring-invoices",
            json={
                "customer_id": cid,
                "name": name,
                "frequency": "monthly",
                "interval_count": 1,
                "due_date_days": 30,
                "line_items": [
                    {"description": "Gen service", "quantity": 1, "unit_price": 50}
                ],
                "next_generation_date": now - 1000,  # Past due
            },
            headers=test_admin_headers,
            timeout=10,
        )

        resp = httpx.post(
            f"{SERVER_URL}/api/recurring-invoices/generate",
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)


class TestRecurringInvoiceErrors:
    """Auth enforcement."""

    def test_unauthorized_list(self, client: httpx.Client):
        resp = client.get("/api/recurring-invoices", timeout=10)
        assert resp.status_code in (401, 403)

    def test_unauthorized_create(self, client: httpx.Client):
        resp = client.post(
            "/api/recurring-invoices",
            json={
                "customer_id": "x",
                "name": "X",
                "frequency": "monthly",
                "interval_count": 1,
                "due_date_days": 30,
            },
            timeout=10,
        )
        assert resp.status_code in (401, 403)

    def test_unauthorized_delete(self, client: httpx.Client):
        resp = client.delete("/api/recurring-invoices/fake-id", timeout=10)
        assert resp.status_code in (401, 403)
