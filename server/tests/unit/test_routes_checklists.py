"""Unit tests for checklist routes."""

from unittest.mock import AsyncMock


def auth_headers(role="admin"):
    import jwt

    from config import settings
    token = jwt.encode({"sub": "u1", "tenant_id": "t1", "role": role},
                       settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


class TestChecklists:
    def test_list_templates(self, client, monkeypatch) -> None:
        mock_paginated = AsyncMock(return_value=([{"id": "c1", "name": "Oil Change", "items": []}], 1))
        monkeypatch.setattr("routes.checklists._paginated", mock_paginated)
        resp = client.get("/api/checklist-templates", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_create_template(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.checklists._call", mock_call)
        monkeypatch.setattr("routes.checklists._log_audit", AsyncMock())
        body = {"name": "Oil Change", "items": [{"task": "Check oil", "order": 1}]}
        resp = client.post("/api/checklist-templates", json=body, headers=auth_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_update_template(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.checklists._call", mock_call)
        monkeypatch.setattr("routes.checklists._log_audit", AsyncMock())
        body = {"name": "Oil Change v2", "items": [{"task": "Check oil", "order": 1}]}
        resp = client.put("/api/checklist-templates/c1", json=body, headers=auth_headers())
        assert resp.status_code == 200

    def test_delete_template(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.checklists._call", mock_call)
        monkeypatch.setattr("routes.checklists._log_audit", AsyncMock())
        resp = client.delete("/api/checklist-templates/c1", headers=auth_headers())
        assert resp.status_code == 200
