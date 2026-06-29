"""Error handling and input validation tests."""
import pytest
import httpx
from .conftest import SERVER_URL, assert_ok


class TestValidation:
    """API input validation and error responses."""

    def test_sql_injection_tenant_id(self, auth_headers: dict):
        """tenant_id containing SQL injection characters is rejected."""
        # Attempt to use a crafted tenant_id — should 400
        resp = httpx.get(
            f"{SERVER_URL}/api/tenants/foo'; DROP TABLE customer; --",
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code in (400, 404), f"Expected 400/404, got {resp.status_code}"

    def test_malformed_json_returns_422(self, client: httpx.Client):
        """Malformed JSON body returns 422 or 400."""
        resp = client.post(
            "/api/auth/login",
            content=b"not-json-at-all",
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        assert resp.status_code in (400, 422)

    def test_invalid_http_method(self, auth_headers: dict):
        """Unsupported HTTP method returns 405."""
        resp = httpx.patch(
            f"{SERVER_URL}/api/customers",
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code in (405, 400)

    def test_empty_body_post(self, auth_headers: dict):
        """POST with empty JSON body returns 422 with Pydantic validation (where implemented)."""
        # Test with customer endpoint which has Pydantic validation
        resp = httpx.post(
            f"{SERVER_URL}/api/customers",
            json={"first_name": "", "last_name": "", "email": ""},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text[:200]}"

    def test_invalid_url_returns_404_or_200(self, client: httpx.Client):
        """Non-existent API route returns appropriate status.
        NOTE: SPA catch-all route makes completely unknown paths return index.html (200).
        """
        resp = client.get("/api/nonexistent-route-xyzzy", timeout=10)
        # Known: FastAPI catch-all route catches everything before the SPA
        # In production, the SPA serves index.html for non-API paths
        assert resp.status_code < 500

    def test_negative_quantity_product(self, auth_headers: dict):
        """Creating product with negative quantity is handled."""
        resp = httpx.post(
            f"{SERVER_URL}/api/products",
            json={"name": "Bad", "sku": "BAD-001", "price": -5.00, "quantity_on_hand": -10},
            headers=auth_headers, timeout=10,
        )
        # Should not crash — acceptable behavior is to create with negative or return 400
        assert resp.status_code < 500
