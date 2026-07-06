"""User management tests."""
import httpx
import pytest
from .conftest import SERVER_URL, assert_ok, unique_suffix, _track_entity


class TestUserCRUD:
    def test_list(self, auth_headers: dict):
        resp = httpx.get(f"{SERVER_URL}/api/users", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "users" in data
        assert "total" in data

    def test_create(self, auth_headers: dict, session_suffix: str):
        suf = unique_suffix()
        email = f"tech-{session_suffix}-{suf}@test.com"
        resp = httpx.post(f"{SERVER_URL}/api/users", json={
            "name": f"Tech User {session_suffix}-{suf}",
            "email": email,
            "role": "tech",
        }, headers=auth_headers, timeout=10)
        assert_ok(resp)

        # Verify it appears in listing
        r2 = httpx.get(f"{SERVER_URL}/api/users", params={"limit": 500}, headers=auth_headers, timeout=10)
        data = r2.json()
        emails = [u.get("email", "") for u in data.get("users", [])]
        assert any(f"tech-{suf}" in e for e in emails)
        # Track the created user for cleanup
        for u in data.get("users", []):
            if u.get("email") == email:
                _track_entity("user", u["id"])
                break

    def test_create_invalid_role(self, auth_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/users", json={
            "name": "Bad", "email": "bad@test.com", "role": "superadmin",
        }, headers=auth_headers, timeout=10)
        assert resp.status_code == 422

    def test_create_missing_name(self, auth_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/users", json={
            "email": "missing@test.com", "role": "tech",
        }, headers=auth_headers, timeout=10)
        assert resp.status_code == 422


class TestUserErrors:
    def test_unauthorized_list(self, client: httpx.Client):
        resp = client.get("/api/users", timeout=10)
        assert resp.status_code in (401, 403)

    def test_unauthorized_create(self, client: httpx.Client):
        resp = client.post("/api/users", json={"name": "X", "email": "x@x.com", "role": "tech"}, timeout=10)
        assert resp.status_code in (401, 403)
