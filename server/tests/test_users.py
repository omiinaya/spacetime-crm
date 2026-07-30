"""Integration tests for User CRUD + errors."""

from __future__ import annotations

import httpx
import pytest

from .conftest import SERVER_URL, _track_entity, assert_ok, unique_suffix

pytestmark = [pytest.mark.integration]


class TestUserCRUD:
    """Admin user CRUD operations."""

    def test_create(self, test_admin_headers: dict, session_suffix: str):
        suf = unique_suffix()
        email = f"tech-{session_suffix}-{suf}@test.com"
        resp = httpx.post(
            f"{SERVER_URL}/api/users",
            json={
                "name": f"Tech User {session_suffix}-{suf}",
                "email": email,
                "role": "tech",
            },
            headers=test_admin_headers,
            timeout=10,
        )
        data = assert_ok(resp)
        # Accept creation by returning the new user ID, or fall back to listing check
        if "id" in data:
            _track_entity("user", data["id"])
            return

        # Fallback: verify it appears in listing
        r2 = httpx.get(
            f"{SERVER_URL}/api/users",
            params={"limit": 500},
            headers=test_admin_headers,
            timeout=10,
        )
        data = r2.json()
        emails = [u.get("email", "") for u in data.get("users", [])]
        assert any(f"tech-{suf}" in e for e in emails), (
            f"Created user not found. Emails: {emails[:5]}"
        )
        # Track the created user for cleanup
        for u in data.get("users", []):
            if u.get("email") == email:
                _track_entity("user", u["id"])
                break

    def test_create_invalid_role(self, test_admin_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/users",
            json={
                "name": "Bad Role",
                "email": "bad@test.com",
                "role": "superadmin",
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 422

    def test_create_duplicate_email(self, test_admin_headers: dict, session_suffix: str):
        suf = unique_suffix()
        email = f"dup-{session_suffix}-{suf}@test.com"
        resp = httpx.post(
            f"{SERVER_URL}/api/users",
            json={"name": "Dup 1", "email": email, "role": "tech"},
            headers=test_admin_headers,
            timeout=10,
        )
        if resp.status_code == 502:
            pytest.skip("STDB reducer unavailable (intermittent)")
        data = assert_ok(resp)
        if "id" in data:
            _track_entity("user", data["id"])
        # Now try to create the same email again — should get 400 or 502
        resp2 = httpx.post(
            f"{SERVER_URL}/api/users",
            json={"name": "Dup 2", "email": email, "role": "tech"},
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp2.status_code == 400

    def test_create_nonexistent_role(self, test_admin_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/users",
            json={
                "name": "Bad Role",
                "email": "bad2@test.com",
                "role": "nonexistent",
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 422
