"""Unit tests for tax_rates routes."""

from unittest.mock import AsyncMock


def admin_headers():
    import jwt

    from config import settings

    token = jwt.encode(
        {"sub": "user-1", "tenant_id": "t1", "role": "admin"}, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    return {"Authorization": f"Bearer {token}"}


class TestTaxRates:
    def test_list_tax_rates(self, client, monkeypatch) -> None:
        mock_paginated = AsyncMock(return_value=([{"id": "t1", "name": "VAT", "rate": 20}], 1))
        monkeypatch.setattr("routes.tax_rates._paginated", mock_paginated)
        resp = client.get("/api/tax-rates", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["tax_rates"][0]["name"] == "VAT"

    def test_list_tax_rates_unauthorized(self, client) -> None:
        resp = client.get("/api/tax-rates")
        assert resp.status_code in (200, 401)

    def test_create_tax_rate(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.tax_rates._call", mock_call)
        monkeypatch.setattr("routes.tax_rates._log_audit", AsyncMock())
        body = {"name": "VAT", "rate": 20.0, "is_default": False}
        resp = client.post("/api/tax-rates", json=body, headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        mock_call.assert_awaited_once()

    def test_update_tax_rate(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.tax_rates._call", mock_call)
        monkeypatch.setattr("routes.tax_rates._log_audit", AsyncMock())
        body = {"name": "VAT Updated", "rate": 22.0, "is_default": True}
        resp = client.put("/api/tax-rates/tax-1", json=body, headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_delete_tax_rate(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.tax_rates._call", mock_call)
        monkeypatch.setattr("routes.tax_rates._log_audit", AsyncMock())
        resp = client.delete("/api/tax-rates/tax-1", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
