"""Customer CRUD and tenant isolation integration tests."""
import pytest
import httpx
from .conftest import SERVER_URL, assert_ok, create_customer, test_admin_headers


class TestCustomerCRUD:
    """Basic customer create, read, update, delete."""

    def test_create_customer(self, test_admin_headers: dict, session_suffix: str):
        """Create a customer returns ok."""
        from .conftest import unique_suffix
        suf = unique_suffix()
        email = f"jane-{session_suffix}-{suf}@example.com"
        resp = httpx.post(
            f"{SERVER_URL}/api/customers",
            json={"first_name": "Jane", "last_name": "Doe", "email": email, "phone": "555-1111"},
            headers=test_admin_headers, timeout=10,
        )
        assert_ok(resp)
        # Verify it appears in search results (scoped by unique email)
        r2 = httpx.get(
            f"{SERVER_URL}/api/customers",
            params={"search": email},
            headers=test_admin_headers, timeout=10,
        )
        data = assert_ok(r2)
        assert any(c["email"] == email for c in data.get("customers", []))

    def test_search_customer(self, test_admin_headers: dict, session_suffix: str):
        """Search by email works."""
        from .conftest import unique_suffix
        suf = unique_suffix()
        email = f"searchme-{session_suffix}-{suf}@example.com"
        customer = create_customer(test_admin_headers, session_suffix=session_suffix, email=email)
        assert customer.get("id"), f"Customer creation failed: {customer}"

        resp = httpx.get(
            f"{SERVER_URL}/api/customers",
            params={"search": email},
            headers=test_admin_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert any(
            c["email"] == email
            for c in data.get("customers", [])
        )

    def test_update_customer(self, test_admin_headers: dict, session_suffix: str):
        """Update customer fields."""
        customer = create_customer(test_admin_headers, session_suffix=session_suffix, first_name="Update", last_name="Test")
        cid = customer.get("id")
        assert cid, f"No customer ID returned: {customer}"

        resp = httpx.put(
            f"{SERVER_URL}/api/customers/{cid}",
            json={"first_name": "Updated", "last_name": "Test", "email": customer["email"], "phone": customer["phone"]},
            headers=test_admin_headers, timeout=10,
        )
        assert_ok(resp)

        # Verify update
        r2 = httpx.get(
            f"{SERVER_URL}/api/customers",
            params={"search": customer["email"]},
            headers=test_admin_headers, timeout=10,
        )
        data = r2.json()
        found = next((c for c in data.get("customers", []) if c["id"] == cid), None)
        assert found is not None
        assert found["first_name"] == "Updated"

    def test_delete_customer(self, test_admin_headers: dict, session_suffix: str):
        """Delete a customer (admin only)."""
        customer = create_customer(test_admin_headers, session_suffix=session_suffix, first_name="Delete", last_name="Me")
        cid = customer.get("id")
        assert cid

        resp = httpx.delete(
            f"{SERVER_URL}/api/customers/{cid}",
            headers=test_admin_headers, timeout=10,
        )
        assert_ok(resp)

        # Verify it's gone
        r2 = httpx.get(
            f"{SERVER_URL}/api/customers",
            params={"search": customer["email"]},
            headers=test_admin_headers, timeout=10,
        )
        data = r2.json()
        assert all(c["id"] != cid for c in data.get("customers", []))


class TestCustomerErrors:
    """Customer endpoint error handling."""

    def test_create_missing_fields(self, test_admin_headers: dict):
        """Missing required fields now return 422 with Pydantic validation."""
        resp = httpx.post(
            f"{SERVER_URL}/api/customers",
            json={"first_name": "", "last_name": "", "email": ""},
            headers=test_admin_headers, timeout=10,
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        assert "detail" in data

    def test_get_nonexistent_customer(self, test_admin_headers: dict):
        """GET non-existent customer returns appropriate error."""
        resp = httpx.get(
            f"{SERVER_URL}/api/customers",
            params={"search": "no-such-email-xyzzy@example.com"},
            headers=test_admin_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert len(data.get("customers", [])) == 0

    def test_delete_nonexistent(self, test_admin_headers: dict):
        """DELETE non-existent ID should not crash."""
        resp = httpx.delete(
            f"{SERVER_URL}/api/customers/nonexistent-id-12345",
            headers=test_admin_headers, timeout=10,
        )
        # STDB may return 200 for delete-nothing — that's acceptable
        assert resp.status_code < 500


class TestSensitiveFieldExclusion:
    """Verify sensitive fields are stripped from customer API responses."""

    SENSITIVE_FIELDS = {"portal_password_hash"}

    def test_list_customers_excludes_sensitive_fields(self, test_admin_headers: dict, session_suffix: str):
        """Customer list endpoint does not return sensitive fields."""
        from .conftest import unique_suffix
        suf = unique_suffix()
        email = f"exclude-test-{session_suffix}-{suf}@example.com"
        customer = create_customer(test_admin_headers, session_suffix=session_suffix, email=email)
        assert customer.get("id"), f"Customer creation failed: {customer}"

        resp = httpx.get(
            f"{SERVER_URL}/api/customers",
            params={"search": email},
            headers=test_admin_headers, timeout=10,
        )
        data = assert_ok(resp)
        for c in data.get("customers", []):
            for field in self.SENSITIVE_FIELDS:
                assert field not in c, (
                    f"Sensitive field '{field}' leaked in customer list response: {c}"
                )

    def test_customer_geolocations_excludes_sensitive_fields(self, test_admin_headers: dict, session_suffix: str):
        """Customer geolocations endpoint does not return sensitive fields."""
        from .conftest import unique_suffix
        suf = unique_suffix()
        email = f"geo-exclude-{session_suffix}-{suf}@example.com"
        customer = create_customer(test_admin_headers, session_suffix=session_suffix, email=email)
        assert customer.get("id"), f"Customer creation failed: {customer}"

        resp = httpx.get(
            f"{SERVER_URL}/api/customers/geolocations",
            headers=test_admin_headers, timeout=10,
        )
        data = assert_ok(resp)
        for loc in data.get("locations", []):
            for field in self.SENSITIVE_FIELDS:
                assert field not in loc, (
                    f"Sensitive field '{field}' leaked in geolocations response"
                )

    def test_find_duplicates_excludes_sensitive_fields(self, test_admin_headers: dict, session_suffix: str):
        """Customer duplicates endpoint does not return sensitive fields."""
        from .conftest import unique_suffix
        suf = unique_suffix()
        email = f"dup-exclude-{session_suffix}-{suf}@example.com"
        # Create two customers with the same email to trigger duplicate detection
        c1 = create_customer(test_admin_headers, session_suffix=session_suffix, email=email)
        c2 = create_customer(test_admin_headers, session_suffix=session_suffix, email=email)
        assert c1.get("id") and c2.get("id")

        resp = httpx.get(
            f"{SERVER_URL}/api/customers/duplicates",
            headers=test_admin_headers, timeout=10,
        )
        data = assert_ok(resp)
        for dup in data.get("duplicates", []):
            for c in dup.get("customers", []):
                for field in self.SENSITIVE_FIELDS:
                    assert field not in c, (
                        f"Sensitive field '{field}' leaked in duplicates response"
                    )


class TestTenantIsolation:
    """Verify tenant_id is correctly set on created entities."""

    def test_customer_has_tenant_id(self, test_admin_headers: dict, session_suffix: str):
        """Created customer has a non-empty tenant_id."""
        customer = create_customer(test_admin_headers, session_suffix=session_suffix, first_name="Tenant", last_name="Check")
        assert customer.get("tenant_id"), f"Missing tenant_id: {customer}"
        assert len(customer["tenant_id"]) > 5, f"tenant_id too short: {customer}"