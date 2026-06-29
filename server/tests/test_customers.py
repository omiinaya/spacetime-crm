"""Customer CRUD and tenant isolation integration tests."""
import pytest
import httpx
from .conftest import SERVER_URL, assert_ok, create_customer


class TestCustomerCRUD:
    """Basic customer create, read, update, delete."""

    def test_create_customer(self, auth_headers: dict):
        """Create a customer returns ok."""
        resp = httpx.post(
            f"{SERVER_URL}/api/customers",
            json={"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com", "phone": "555-1111"},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)
        # Verify it appears in list
        r2 = httpx.get(
            f"{SERVER_URL}/api/customers",
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(r2)
        emails = [c["email"] for c in data.get("customers", [])]
        assert "jane@example.com" in emails

    def test_search_customer(self, auth_headers: dict):
        """Search by email works."""
        customer = create_customer(auth_headers, email="searchme@example.com")
        assert customer.get("id"), f"Customer creation failed: {customer}"

        resp = httpx.get(
            f"{SERVER_URL}/api/customers",
            params={"search": "searchme@example.com"},
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert any(
            c["email"] == "searchme@example.com"
            for c in data.get("customers", [])
        )

    def test_update_customer(self, auth_headers: dict):
        """Update customer fields."""
        customer = create_customer(auth_headers, first_name="Update", last_name="Test")
        cid = customer.get("id")
        assert cid, f"No customer ID returned: {customer}"

        resp = httpx.put(
            f"{SERVER_URL}/api/customers/{cid}",
            json={"first_name": "Updated", "last_name": "Test", "email": customer["email"], "phone": customer["phone"]},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

        # Verify update
        r2 = httpx.get(
            f"{SERVER_URL}/api/customers",
            params={"search": customer["email"]},
            headers=auth_headers, timeout=10,
        )
        data = r2.json()
        found = next((c for c in data.get("customers", []) if c["id"] == cid), None)
        assert found is not None
        assert found["first_name"] == "Updated"

    def test_delete_customer(self, auth_headers: dict):
        """Delete a customer (admin only)."""
        customer = create_customer(auth_headers, first_name="Delete", last_name="Me")
        cid = customer.get("id")
        assert cid

        resp = httpx.delete(
            f"{SERVER_URL}/api/customers/{cid}",
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

        # Verify it's gone
        r2 = httpx.get(
            f"{SERVER_URL}/api/customers",
            params={"search": customer["email"]},
            headers=auth_headers, timeout=10,
        )
        data = r2.json()
        assert all(c["id"] != cid for c in data.get("customers", []))


class TestCustomerErrors:
    """Customer endpoint error handling."""

    def test_create_missing_fields(self, auth_headers: dict):
        """Missing required fields now return 422 with Pydantic validation."""
        resp = httpx.post(
            f"{SERVER_URL}/api/customers",
            json={"first_name": "", "last_name": "", "email": ""},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert "detail" in data

    def test_get_nonexistent_customer(self, auth_headers: dict):
        """GET non-existent customer returns appropriate error."""
        resp = httpx.get(
            f"{SERVER_URL}/api/customers",
            params={"search": "no-such-email-xyzzy@example.com"},
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert len(data.get("customers", [])) == 0

    def test_delete_nonexistent(self, auth_headers: dict):
        """DELETE non-existent ID should not crash."""
        resp = httpx.delete(
            f"{SERVER_URL}/api/customers/nonexistent-id-12345",
            headers=auth_headers, timeout=10,
        )
        # STDB may return 200 for delete-nothing — that's acceptable
        assert resp.status_code < 500


class TestTenantIsolation:
    """Verify tenant_id is correctly set on created entities."""

    def test_customer_has_tenant_id(self, auth_headers: dict):
        """Created customer has a non-empty tenant_id."""
        customer = create_customer(auth_headers, first_name="Tenant", last_name="Check")
        assert customer.get("tenant_id"), f"Missing tenant_id: {customer}"
        assert len(customer["tenant_id"]) > 5, f"tenant_id too short: {customer}"
