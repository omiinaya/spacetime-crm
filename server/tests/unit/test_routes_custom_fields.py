"""Unit tests for custom fields routes."""

from unittest.mock import AsyncMock


def auth_headers(role="admin"):
    import jwt
    from config import settings
    token = jwt.encode({"sub": "u1", "tenant_id": "t1", "role": role},
                       settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


class TestCustomFields:
    def test_list_definitions(self, client, monkeypatch):
        mock_paginated = AsyncMock(return_value=([{"id": "cf1", "label": "VIN", "field_type": "text"}], 1))
        monkeypatch.setattr("routes.custom_fields._paginated", mock_paginated)
        resp = client.get("/api/custom-field-definitions", headers=auth_headers())
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_create_definition(self, client, monkeypatch):
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.custom_fields._call", mock_call)
        monkeypatch.setattr("routes.custom_fields._log_audit", AsyncMock())
        body = {
            "entity_type": "customer",
            "label": "VIN",
            "field_type": "text",
            "options": [],
            "sort_order": 0,
            "required": False,
            "active": True
        }
        resp = client.post("/api/custom-field-definitions", json=body, headers=auth_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_update_definition(self, client, monkeypatch):
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.custom_fields._call", mock_call)
        monkeypatch.setattr("routes.custom_fields._log_audit", AsyncMock())
        body = {
            "entity_type": "customer",
            "label": "VIN Updated",
            "field_type": "text",
            "options": [],
            "sort_order": 1,
            "required": True,
            "active": True
        }
        resp = client.put("/api/custom-field-definitions/cf1", json=body, headers=auth_headers())
        assert resp.status_code == 200

    def test_delete_definition(self, client, monkeypatch):
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.custom_fields._call", mock_call)
        monkeypatch.setattr("routes.custom_fields._log_audit", AsyncMock())
        resp = client.delete("/api/custom-field-definitions/cf1", headers=auth_headers())
        assert resp.status_code == 200

    def test_get_field_values(self, client, monkeypatch):
        mock_sql = AsyncMock(return_value=[{"id": "v1", "field_id": "cf1", "value": "abc"}])
        monkeypatch.setattr("routes.custom_fields._sql", mock_sql)
        resp = client.get("/api/custom-field-values/cust-1", headers=auth_headers())
        assert resp.status_code == 200
        assert len(resp.json()["values"]) == 1

    def test_set_field_values(self, client, monkeypatch):
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.custom_fields._call", mock_call)
        body = {"values": {"cf1": "abc123"}}
        resp = client.put("/api/custom-field-values/cust-1", json=body, headers=auth_headers())
        assert resp.status_code == 200
