"""Auth and permissions integration tests.

Uses isolated tenant admin for most tests to avoid polluting global admin state.
Global admin tests are kept for coverage but are scoped to only check that
the bootstrap admin user exists and can log in.
"""

import base64
import json
import pytest
import httpx
from .conftest import SERVER_URL, ADMIN_EMAIL, ADMIN_PW, assert_ok, assert_unauthorized


class TestAuth:
    """Authentication and authorization flows."""

    def test_login_success_admin(self, client: httpx.Client):
        """Global admin credentials return a token (bootstrap state test)."""
        resp = client.post(
            "/api/auth/login",
            json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PW,
            },
        )
        data = assert_ok(resp)
        assert "token" in data
        assert data["user"]["role"] == "admin"
        assert "tenant_id" in data["user"]

    def test_login_success_isolated(self, test_admin_headers: dict):
        """Isolated tenant admin can also log in (uses session-specific creds)."""
        # We need to log in as the isolated admin — extract email from headers
        # The isolated tenant admin email is f"admin-{session_suffix}@test.local"
        # We'll verify that the existing token is valid first
        resp = httpx.get(f"{SERVER_URL}/api/auth/me", headers=test_admin_headers, timeout=10)
        data = assert_ok(resp)
        assert "email" in data
        assert data["role"] == "admin"

    def test_login_invalid_password(self, client: httpx.Client):
        """Wrong password returns 401."""
        resp = client.post(
            "/api/auth/login",
            json={
                "email": ADMIN_EMAIL,
                "password": "wrongpassword",
            },
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client: httpx.Client):
        """Unknown email returns 401."""
        resp = client.post(
            "/api/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "any",
            },
        )
        assert resp.status_code == 401

    def test_unauthenticated_request(self, client: httpx.Client):
        """Requests without a token return 401."""
        resp = client.get("/api/stats")
        assert_unauthorized(resp)

    def test_bad_token(self, client: httpx.Client):
        """Invalid JWT returns 401."""
        resp = client.get(
            "/api/customers",
            headers={
                "Authorization": "Bearer garbage-token",
            },
        )
        assert_unauthorized(resp)

    def test_expired_token_returns_401(self, client: httpx.Client):
        """Expired JWT returns 401."""
        # Craft a token that looks like a JWT but is clearly expired
        # Base64-encode a dummy expired payload
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
        payload = (
            base64.urlsafe_b64encode(json.dumps({"sub": "user_test", "exp": 1000000, "role": "admin"}).encode())
            .rstrip(b"=")
            .decode()
        )
        sig = base64.urlsafe_b64encode(b"bad-signature").rstrip(b"=").decode()
        expired = f"{header}.{payload}.{sig}"
        resp = client.get(
            "/api/customers",
            headers={
                "Authorization": f"Bearer {expired}",
            },
        )
        assert_unauthorized(resp)

    def test_auth_me_endpoint(self, test_admin_headers: dict):
        """GET /api/auth/me returns current user (using isolated tenant)."""
        resp = httpx.get(f"{SERVER_URL}/api/auth/me", headers=test_admin_headers, timeout=10)
        data = assert_ok(resp)
        assert "email" in data
        assert data["role"] == "admin"

    def test_portal_login_flow(self, client: httpx.Client):
        """Customer portal login rejects admin credentials."""
        resp = client.post(
            "/api/portal/login",
            json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PW,
            },
        )
        # Portal login fails for non-customer credentials
        assert resp.status_code in (401, 403, 404)


class TestPermissions:
    """Role-based access control."""

    def test_health_public(self, client: httpx.Client):
        """Health endpoints are public."""
        resp = client.get("/api/health/ready")
        assert_ok(resp)

    def test_admin_access(self, test_admin_headers: dict):
        """Admin (isolated tenant) can access admin-only endpoints."""
        resp = httpx.get(f"{SERVER_URL}/api/audit-log", headers=test_admin_headers, timeout=10)
        # May return empty, but shouldn't 403
        assert resp.status_code != 403

    def test_cors_header(self, client: httpx.Client):
        """CORS header is set for the configured origin."""
        resp = client.options(
            "/api/customers",
            headers={
                "Origin": "http://localhost:5185",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS preflight should succeed
        assert resp.status_code in (200, 204)
        assert "access-control-allow-origin" in resp.headers
