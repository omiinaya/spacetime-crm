"""Unit tests for users routes."""

from unittest.mock import AsyncMock


def admin_headers():
    import jwt
    from config import settings
    token = jwt.encode({"sub": "user-1", "tenant_id": "t1", "role": "admin"},
                       settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


class TestUsers:
    def test_list_users(self, client, monkeypatch):
        mock_paginated = AsyncMock(return_value=([{"id": "u1", "name": "Alice", "role": "tech"}], 1))
        monkeypatch.setattr("routes.users._paginated", mock_paginated)
        resp = client.get("/api/users", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_users_no_auth(self, client):
        resp = client.get("/api/users")
        assert resp.status_code == 401

    def test_create_user(self, client, monkeypatch):
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.users._call", mock_call)
        monkeypatch.setattr("routes.users._log_audit", AsyncMock())
        body = {"name": "Bob", "email": "bob@crm.local", "role": "tech"}
        resp = client.post("/api/users", json=body, headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        mock_call.assert_awaited_once()

    def test_get_user_settings(self, client, monkeypatch):
        mock_sql = AsyncMock(return_value=[{"theme": "dark", "default_ticket_status": "open"}])
        monkeypatch.setattr("routes.users._sql", mock_sql)
        resp = client.get("/api/users/settings", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["settings"]["theme"] == "dark"

    def test_get_user_settings_not_found(self, client, monkeypatch):
        mock_sql = AsyncMock(return_value=[])
        monkeypatch.setattr("routes.users._sql", mock_sql)
        resp = client.get("/api/users/settings", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["settings"] is None

    def test_update_user_settings(self, client, monkeypatch):
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.users._call", mock_call)
        monkeypatch.setattr("routes.users._log_audit", AsyncMock())
        body = {"theme": "dark", "default_ticket_status": "in_progress"}
        resp = client.put("/api/users/settings", json=body, headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
