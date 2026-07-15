"""Unit tests for customer routes."""

from unittest.mock import AsyncMock


def admin_headers():
    import jwt
    from config import settings

    token = jwt.encode(
        {"sub": "user-1", "tenant_id": "t1", "role": "admin"}, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    return {"Authorization": f"Bearer {token}"}


class TestCustomers:
    def test_list_customers(self, client, monkeypatch) -> None:
        mock_paginated = AsyncMock(return_value=([{"id": "c1", "first_name": "John", "last_name": "Doe"}], 1))
        monkeypatch.setattr("routes.customers._paginated", mock_paginated)
        resp = client.get("/api/customers", headers=admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_list_customers_search(self, client, monkeypatch) -> None:
        mock_paginated = AsyncMock(return_value=([{"id": "c1", "first_name": "John", "last_name": "Doe"}], 1))
        monkeypatch.setattr("routes.customers._paginated", mock_paginated)
        resp = client.get("/api/customers?search=John", headers=admin_headers())
        assert resp.status_code == 200

    def test_create_customer(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={"id": "new-c1"})
        monkeypatch.setattr("routes.customers._call", mock_call)
        monkeypatch.setattr("routes.customers._log_audit", AsyncMock())
        body = {"first_name": "Jane", "last_name": "Smith", "email": "jane@example.com", "phone": "+15551234567"}
        resp = client.post("/api/customers", json=body, headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_create_customer_minimal(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={"id": "new-c2"})
        monkeypatch.setattr("routes.customers._call", mock_call)
        monkeypatch.setattr("routes.customers._log_audit", AsyncMock())
        body = {"first_name": "Bob", "last_name": "Jones"}
        resp = client.post("/api/customers", json=body, headers=admin_headers())
        assert resp.status_code == 200

    def test_create_customer_invalid(self, client, monkeypatch) -> None:
        body = {"first_name": ""}
        resp = client.post("/api/customers", json=body, headers=admin_headers())
        assert resp.status_code == 422

    def test_update_customer(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.customers._call", mock_call)
        monkeypatch.setattr("routes.customers._log_audit", AsyncMock())
        body = {"first_name": "Jane", "last_name": "Smith"}
        resp = client.put("/api/customers/c1", json=body, headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_delete_customer(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.customers._call", mock_call)
        monkeypatch.setattr("routes.customers._log_audit", AsyncMock())
        resp = client.delete("/api/customers/c1", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_geolocations(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(
            side_effect=[
                [{"id": "c1", "latitude": 40.7128, "longitude": -74.0060}],
                [{"customer_id": "c1", "latitude": 40.7128, "longitude": -74.0060}],
            ]
        )
        monkeypatch.setattr("routes.customers._sql_t", mock_sql)
        resp = client.get("/api/customers/geolocations", headers=admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["locations"]) > 0

    def test_geocode_customer(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(
            side_effect=[
                [{"id": "c1", "address_line1": "123 Main St", "city": "New York", "state": "NY", "zip": "10001"}],
                [{"id": "c1", "latitude": 40.7128, "longitude": -74.0060}],
            ]
        )
        monkeypatch.setattr("routes.customers._sql", mock_sql)
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.customers._call", mock_call)
        monkeypatch.setattr("routes.customers._log_audit", AsyncMock())
        from unittest.mock import AsyncMock as AMock

        mock_client = AMock()
        mock_resp = AMock()
        mock_resp.status_code = 200
        mock_resp.json = lambda: [{"lat": "40.7128", "lon": "-74.0060"}]
        mock_client.get = AMock(return_value=mock_resp)
        monkeypatch.setattr("routes.customers.get_http_client", lambda: mock_client)
        resp = client.post("/api/customers/c1/geocode", headers=admin_headers())
        assert resp.status_code == 200

    def test_duplicates(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(
            return_value=[
                {"id": "c1", "first_name": "John", "last_name": "Doe", "email": "john@example.com", "_count": 2}
            ]
        )
        monkeypatch.setattr("routes.customers._sql", mock_sql)
        resp = client.get("/api/customers/duplicates", headers=admin_headers())
        assert resp.status_code == 200

    def test_portal_password(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.customers._call", mock_call)
        monkeypatch.setattr("routes.customers._log_audit", AsyncMock())
        body = {"password": "newpassword123"}
        resp = client.post("/api/customers/c1/portal-password", json=body, headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
