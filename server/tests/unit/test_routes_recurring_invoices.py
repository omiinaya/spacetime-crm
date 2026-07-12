"""Unit tests for recurring invoice routes."""

from unittest.mock import AsyncMock


def admin_headers():
    import jwt
    from config import settings
    token = jwt.encode({"sub": "user-1", "tenant_id": "t1", "role": "admin"},
                       settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


class TestRecurringInvoices:
    def test_list_rules(self, client, monkeypatch):
        mock_sql = AsyncMock(return_value=[{"id": "r1", "name": "Monthly rent"}])
        monkeypatch.setattr("routes.recurring_invoices._sql", mock_sql)
        resp = client.get("/api/recurring-invoices", headers=admin_headers())
        assert resp.status_code == 200

    def test_create_rule(self, client, monkeypatch):
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.recurring_invoices._call", mock_call)
        monkeypatch.setattr("routes.recurring_invoices._log_audit", AsyncMock())
        monkeypatch.setattr("routes.recurring_invoices._fire_webhook", AsyncMock())
        body = {
            "customer_id": "c1",
            "line_items": [{"description": "Rent", "quantity": 1, "unit_price": 1000}],
            "frequency": "monthly",
            "day_of_month": 1,
        }
        resp = client.post("/api/recurring-invoices", json=body, headers=admin_headers())
        assert resp.status_code == 200

    def test_delete_rule(self, client, monkeypatch):
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.recurring_invoices._call", mock_call)
        monkeypatch.setattr("routes.recurring_invoices._log_audit", AsyncMock())
        resp = client.delete("/api/recurring-invoices/r1", headers=admin_headers())
        assert resp.status_code == 200
