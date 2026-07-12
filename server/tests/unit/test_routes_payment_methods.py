"""Unit tests for payment methods routes."""

from unittest.mock import AsyncMock, patch


def auth_headers(role="admin"):
    import jwt
    from config import settings
    token = jwt.encode({"sub": "u1", "tenant_id": "t1", "role": role},
                       settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


class TestPaymentMethods:
    def test_list_methods(self, client, monkeypatch):
        mock_sql = AsyncMock(return_value=[{"id": "pm1", "type": "card", "last4": "4242"}])
        monkeypatch.setattr("routes.payment_methods._sql", mock_sql)
        resp = client.get("/api/payment-methods?customer_id=c1", headers=auth_headers())
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_create_method(self, client, monkeypatch):
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.payment_methods._call", mock_call)
        monkeypatch.setattr("routes.payment_methods._log_audit", AsyncMock())
        body = {
            "customer_id": "c1",
            "stripe_payment_method_id": "pm_xyz",
            "brand": "Visa",
            "last4": "4242",
            "exp_month": 12,
            "exp_year": 2030,
        }
        resp = client.post("/api/payment-methods", json=body, headers=auth_headers())
        assert resp.status_code == 200

    def test_delete_method(self, client, monkeypatch):
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.payment_methods._call", mock_call)
        monkeypatch.setattr("routes.payment_methods._log_audit", AsyncMock())
        resp = client.delete("/api/payment-methods/pm1", headers=auth_headers())
        assert resp.status_code == 200

    def test_set_default(self, client, monkeypatch):
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.payment_methods._call", mock_call)
        monkeypatch.setattr("routes.payment_methods._log_audit", AsyncMock())
        body = {"customer_id": "c1"}
        resp = client.put("/api/payment-methods/pm1/default", json=body, headers=auth_headers())
        assert resp.status_code == 200
