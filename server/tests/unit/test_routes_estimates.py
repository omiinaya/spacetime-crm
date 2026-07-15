"""Unit tests for estimate routes."""

from unittest.mock import AsyncMock


def admin_headers():
    import jwt

    from config import settings

    token = jwt.encode(
        {"sub": "user-1", "tenant_id": "t1", "role": "admin"}, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    return {"Authorization": f"Bearer {token}"}


class TestEstimates:
    def test_list_estimates(self, client, monkeypatch) -> None:
        mock_paginated = AsyncMock(return_value=([{"id": "e1", "number": "EST-001", "status": "draft"}], 1))
        monkeypatch.setattr("routes.estimates._paginated", mock_paginated)
        resp = client.get("/api/estimates", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_create_estimate(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.estimates._call", mock_call)
        monkeypatch.setattr("routes.estimates._log_audit", AsyncMock())
        monkeypatch.setattr("routes.estimates._fire_webhook", AsyncMock())
        body = {
            "customer_id": "c1",
            "line_items": [{"description": "Brake pads", "quantity": 2, "unit_price": 50.0}],
            "notes": "",
            "terms": "",
            "valid_until_days": 30,
        }
        resp = client.post("/api/estimates", json=body, headers=admin_headers())
        assert resp.status_code == 200

    def test_update_estimate_status(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.estimates._call", mock_call)
        monkeypatch.setattr("routes.estimates._log_audit", AsyncMock())
        body = {"status": "approved"}
        resp = client.put("/api/estimates/e1/status", json=body, headers=admin_headers())
        assert resp.status_code == 200
