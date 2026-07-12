"""Unit tests for POS / counter sale routes."""

from unittest.mock import AsyncMock


def admin_headers():
    import jwt

    from config import settings
    token = jwt.encode({"sub": "user-1", "tenant_id": "t1", "role": "admin"},
                       settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


class TestPOS:
    def test_list_sales(self, client, monkeypatch) -> None:
        mock_paginated = AsyncMock(return_value=([{"id": "s1", "total": 100}], 1))
        monkeypatch.setattr("routes.pos._paginated", mock_paginated)
        resp = client.get("/api/pos/sales", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_get_sale(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(return_value=[{"id": "s1", "total": 100}])
        monkeypatch.setattr("routes.pos._sql", mock_sql)
        resp = client.get("/api/pos/sales/s1", headers=admin_headers())
        assert resp.status_code == 200

    def test_get_sale_not_found(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(return_value=[])
        monkeypatch.setattr("routes.pos._sql", mock_sql)
        resp = client.get("/api/pos/sales/nonexistent", headers=admin_headers())
        assert resp.status_code == 404

    def test_create_sale(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={"id": "sale-1"})
        monkeypatch.setattr("routes.pos._call", mock_call)
        monkeypatch.setattr("routes.pos._log_audit", AsyncMock())
        monkeypatch.setattr("routes.pos._fire_webhook", AsyncMock())
        body = {"customer_id": "c1", "items": [{"product_id": "p1", "qty": 2}], "payments": [{"method": "cash", "amount": 100.0}]}
        resp = client.post("/api/pos/create", json=body, headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["id"] == "sale-1"

    def test_add_item(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.pos._call", mock_call)
        body = {"product_id": "p1", "qty": 1}
        resp = client.post("/api/pos/items", json=body, headers=admin_headers())
        assert resp.status_code == 200
