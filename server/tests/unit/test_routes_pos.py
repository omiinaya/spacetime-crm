"""Unit tests for POS / counter sale routes."""

from unittest.mock import AsyncMock


def admin_headers():
    import jwt

    from config import settings

    token = jwt.encode(
        {"sub": "user-1", "tenant_id": "t1", "role": "admin"}, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    return {"Authorization": f"Bearer {token}"}


class TestPOS:
    def test_list_sales(self, client, monkeypatch) -> None:
        mock_paginated = AsyncMock(return_value=([{"id": "s1", "total": 100}], 1))
        monkeypatch.setattr("routes.pos._paginated", mock_paginated)
        resp = client.get("/api/pos/sales", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_get_sale(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(
            side_effect=[
                [{"id": "s1", "total": 100}],  # sale query
                [],  # items query (empty to avoid self-reference)
            ]
        )
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
        monkeypatch.setattr("helpers._fire_webhook", AsyncMock())
        body = {
            "customer_id": "c1",
            "customer_name": "Test Customer",
            "payment_method": "cash",
            "amount_tendered": 100.0,
            "tax_rate": 8.5,
            "discount_amount": 0,
            "currency": "USD",
        }
        resp = client.post("/api/pos/create", json=body, headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_add_item(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.pos._call", mock_call)
        body = {"sale_id": "s1", "product_id": "p1", "product_name": "Test Product", "quantity": 1, "unit_price": 10.0}
        resp = client.post("/api/pos/items", json=body, headers=admin_headers())
        assert resp.status_code == 200
