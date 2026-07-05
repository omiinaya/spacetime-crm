"""Tenant management integration tests."""
import pytest
import httpx
import uuid
from .conftest import SERVER_URL, assert_ok


class TestTenants:
    """Multi-tenant CRUD and member management."""

    def test_list_tenants(self, auth_headers: dict):
        """Admin can list all tenants."""
        resp = httpx.get(f"{SERVER_URL}/api/tenants", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "tenants" in data
        assert len(data["tenants"]) >= 1  # At least the default tenant

    def test_get_tenant(self, auth_headers: dict, admin_user: dict):
        """Admin can fetch a specific tenant."""
        tid = admin_user.get("tenant_id")
        assert tid, "Admin has no tenant_id"
        resp = httpx.get(f"{SERVER_URL}/api/tenants/{tid}", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "tenant" in data
        assert data["tenant"]["id"] == tid

    def test_create_tenant(self, auth_headers: dict):
        """Create a new tenant."""
        slug = f"test-tenant-{uuid.uuid4().hex[:8]}"
        resp = httpx.post(
            f"{SERVER_URL}/api/tenants",
            json={"name": "Test Tenant", "slug": slug},
            headers=auth_headers, timeout=10,
        )
        data = assert_ok(resp)
        assert data.get("ok") is True

    def test_tenant_members(self, auth_headers: dict, admin_user: dict):
        """Tenant members list includes admin."""
        tid = admin_user["tenant_id"]
        resp = httpx.get(f"{SERVER_URL}/api/tenants/{tid}", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        tenant = data["tenant"]
        assert "members" in tenant
        member_names = [m["username"] for m in tenant["members"]]
        assert admin_user["name"] in member_names, f"Admin {admin_user['name']} not in {member_names}"

    def test_unauthenticated_tenant_access(self, client: httpx.Client):
        """Unauthenticated requests to tenant endpoints fail."""
        resp = client.get("/api/tenants")
        assert resp.status_code in (401, 403)

    def test_tenant_update(self, auth_headers: dict, admin_user: dict):
        """Update tenant settings."""
        tid = admin_user["tenant_id"]
        resp = httpx.put(
            f"{SERVER_URL}/api/tenants/{tid}",
            json={"name": "Updated Shop", "slug": "updated-shop"},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

        # Restore
        resp = httpx.put(
            f"{SERVER_URL}/api/tenants/{tid}",
            json={"name": "Main Shop", "slug": "main-shop"},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)
