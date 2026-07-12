"""Unit tests for purchase order routes."""

from unittest.mock import AsyncMock


def admin_headers():
    import jwt
    from config import settings
    token = jwt.encode({"sub": "user-1", "tenant_id": "t1", "role": "admin"},
                       settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


class TestPurchaseOrders:
    def test_list_pos(self, client, monkeypatch):
        mock_paginated = AsyncMock(return_value=([{"id": "po1", "number": "PO-001", "status": "pending"}], 1))
        monkeypatch.setattr("routes.purchase_orders._paginated", mock_paginated)
        resp = client.get("/api/purchase-orders", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_get_po_not_found(self, client, monkeypatch):
        mock_sql = AsyncMock(return_value=[])
        monkeypatch.setattr("routes.purchase_orders._sql", mock_sql)
        resp = client.get("/api/purchase-orders/nonexistent", headers=admin_headers())
        assert resp.status_code == 404

    def test_get_po(self, client, monkeypatch):
        mock_sql = AsyncMock(return_value=[{"id": "po1", "number": "PO-001"}])
        monkeypatch.setattr("routes.purchase_orders._sql", mock_sql)
        resp = client.get("/api/purchase-orders/po1", headers=admin_headers())
        assert resp.status_code == 200

    def test_create_po(self, client, monkeypatch):
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.purchase_orders._call", mock_call)
        monkeypatch.setattr("routes.purchase_orders._log_audit", AsyncMock())
        body = {"vendor": "AutoZone", "items": [{"sku": "123", "qty": 5, "unit_cost": 10.0}], "notes": ""}
        resp = client.post("/api/purchase-orders", json=body, headers=admin_headers())
        assert resp.status_code == 200
