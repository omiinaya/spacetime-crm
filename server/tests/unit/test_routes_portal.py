"""Unit tests for customer portal routes."""

from __future__ import annotations

import sys
from pathlib import Path

_server_dir = str(Path(__file__).resolve().parent.parent.parent)
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

from unittest.mock import AsyncMock, MagicMock

CUSTOMER_RECORD = {"id": "cust-1", "email": "cust@test.com", "first_name": "Test", "last_name": "User", "tenant_id": "t1", "active": True}


def admin_headers():
    import jwt
    from config import settings
    token = jwt.encode({"sub": "user-1", "tenant_id": "t1", "role": "admin"},
                       settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


def customer_headers():
    import jwt
    from config import settings
    token = jwt.encode({"sub": "cust-1", "tenant_id": "t1", "role": "customer", "email": "cust@test.com", "type": "portal"},
                       settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


class TestPortalLogin:
    def test_login_success(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [{"id": "cust-1", "email": "cust@test.com", "portal_password_hash": "$2b$12$H7ThDUqjqLiAEceVCZbKRukeWxqMzPHzY69Vt3SMiNkr3ObPHvNOm", "tenant_id": "t1"}],
        ])
        monkeypatch.setattr("routes.portal._sql", mock_sql)
        resp = client.post("/api/portal/login", json={"email": "cust@test.com", "password": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["customer"]["email"] == "cust@test.com"

    def test_login_invalid_credentials(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(return_value=[])
        monkeypatch.setattr("routes.portal._sql", mock_sql)
        resp = client.post("/api/portal/login", json={"email": "wrong@test.com", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_missing_fields(self, client) -> None:
        resp = client.post("/api/portal/login", json={})
        assert resp.status_code == 422


class TestPortalMe:
    def test_get_profile(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [CUSTOMER_RECORD],
        ])
        monkeypatch.setattr("routes.portal._sql", mock_sql)
        resp = client.get("/api/portal/me", headers=customer_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "cust-1"

    def test_get_profile_unauthorized(self, client) -> None:
        resp = client.get("/api/portal/me")
        assert resp.status_code == 401


class TestPortalStats:
    def test_get_stats(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [CUSTOMER_RECORD],
            [{"count": 3}],
            [{"count": 2}],
            [{"count": 1}],
        ])
        monkeypatch.setattr("routes.portal._sql", mock_sql)
        resp = client.get("/api/portal/stats", headers=customer_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "open_tickets" in data


class TestPortalTickets:
    def test_list_tickets(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [CUSTOMER_RECORD],
            [{"id": "tkt-1", "subject": "Test", "status": "open", "created_at": "2024-01-01"}],
            [{"id": "u1", "name": "Tech Support"}],
        ])
        monkeypatch.setattr("routes.portal._sql", mock_sql)
        resp = client.get("/api/portal/tickets", headers=customer_headers())
        assert resp.status_code == 200

    def test_ticket_detail(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [CUSTOMER_RECORD],
            [{"id": "tkt-1", "subject": "Test", "status": "open", "customer_id": "cust-1", "tenant_id": "t1"}],
            [{"id": "n1", "note": "Test note", "created_at": "2024-01-01"}],
            [{"id": "u1", "name": "Tech Support"}],
        ])
        monkeypatch.setattr("routes.portal._sql", mock_sql)
        resp = client.get("/api/portal/tickets/tkt-1", headers=customer_headers())
        assert resp.status_code == 200


class TestPortalInvoices:
    def test_list_invoices(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [CUSTOMER_RECORD],
            [{"id": "inv-1", "invoice_number": 1001, "status": "sent", "total": "100.00", "created_at": "2024-01-01"}],
        ])
        monkeypatch.setattr("routes.portal._sql", mock_sql)
        resp = client.get("/api/portal/invoices", headers=customer_headers())
        assert resp.status_code == 200

    def test_invoice_detail(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [CUSTOMER_RECORD],
            [{"id": "inv-1", "invoice_number": 1001, "status": "sent", "total": "100.00", "customer_id": "cust-1", "tenant_id": "t1"}],
            [{"id": "li-1", "description": "Test item", "quantity": 1, "unit_price": "100.00", "sort_order": 1}],
            [{"id": "pm-1", "amount": "50.00", "created_at": "2024-01-01"}],
        ])
        monkeypatch.setattr("routes.portal._sql", mock_sql)
        resp = client.get("/api/portal/invoices/inv-1", headers=customer_headers())
        assert resp.status_code == 200


class TestPortalNotes:
    def test_add_note(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [CUSTOMER_RECORD],
            [{"id": "tkt-1", "customer_id": "cust-1", "tenant_id": "t1"}],
        ])
        monkeypatch.setattr("routes.portal._sql", mock_sql)
        monkeypatch.setattr("routes.portal._call", AsyncMock(return_value={}))
        resp = client.post("/api/portal/tickets/tkt-1/notes", json={"note": "Test note", "content": "Test note"}, headers=customer_headers())
        assert resp.status_code == 200


class TestPortalSetPassword:
    def test_set_password(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [CUSTOMER_RECORD],
        ])
        monkeypatch.setattr("routes.portal._sql", mock_sql)
        monkeypatch.setattr("routes.portal._call", AsyncMock(return_value={}))
        resp = client.post("/api/portal/customer/set-password", json={"password": "newpass123"}, headers=customer_headers())
        assert resp.status_code == 200

    def test_set_password_weak(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [CUSTOMER_RECORD],
        ])
        monkeypatch.setattr("routes.portal._sql", mock_sql)
        resp = client.post("/api/portal/customer/set-password", json={"password": "weak"}, headers=customer_headers())
        assert resp.status_code == 422


class TestPortalAppointments:
    def test_list_appointments(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [CUSTOMER_RECORD],
            [{"id": "apt-1", "title": "Consultation", "start_time": 1750000000000, "end_time": 1750003600000}],
        ])
        monkeypatch.setattr("routes.portal._sql", mock_sql)
        resp = client.get("/api/portal/appointments", headers=customer_headers())
        assert resp.status_code == 200


class TestPortalPaymentMethods:
    def test_list_payment_methods(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [CUSTOMER_RECORD],
            [{"id": "pm-1", "last_four": "4242", "brand": "Visa", "exp_month": 12, "exp_year": 2026}],
        ])
        monkeypatch.setattr("routes.portal._sql", mock_sql)
        resp = client.get("/api/portal/payment-methods", headers=customer_headers())
        assert resp.status_code == 200
