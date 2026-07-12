"""Unit tests for invoice routes."""

from unittest.mock import AsyncMock


def admin_headers():
    import jwt
    from config import settings
    token = jwt.encode({"sub": "user-1", "tenant_id": "t1", "role": "admin"},
                       settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


class TestInvoices:
    def test_list_invoices(self, client, monkeypatch) -> None:
        mock_paginated = AsyncMock(return_value=([{"id": "inv1", "number": "INV-001", "total": 100}], 1))
        monkeypatch.setattr("routes.invoices._paginated", mock_paginated)
        resp = client.get("/api/invoices", headers=admin_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

    def test_create_invoice(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.invoices._call", mock_call)
        monkeypatch.setattr("routes.invoices._log_audit", AsyncMock())
        monkeypatch.setattr("routes.invoices._fire_webhook", AsyncMock())
        monkeypatch.setattr("routes.invoices._mail_customer_email", lambda x: "")
        monkeypatch.setattr("routes.invoices._sms_customer_phone", lambda x: "")
        body = {"customer_id": "c1", "line_items": [{"description": "Service", "quantity": 1, "unit_price": 100}]}
        resp = client.post("/api/invoices", json=body, headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_update_invoice_status(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.invoices._call", mock_call)
        monkeypatch.setattr("routes.invoices._log_audit", AsyncMock())
        monkeypatch.setattr("routes.invoices._fire_webhook", AsyncMock())
        body = {"status": "paid"}
        resp = client.put("/api/invoices/inv1/status", json=body, headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_bulk_status_update(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.invoices._call", mock_call)
        monkeypatch.setattr("routes.invoices._log_audit", AsyncMock())
        body = {"invoice_ids": ["inv1", "inv2"], "status": "cancelled"}
        resp = client.post("/api/invoices/bulk-status-update", json=body, headers=admin_headers())
        assert resp.status_code == 200

    def test_bulk_edit(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.invoices._call", mock_call)
        monkeypatch.setattr("routes.invoices._log_audit", AsyncMock())
        body = {"invoice_ids": ["inv1", "inv2"], "terms": "Net 30", "notes": "Updated terms"}
        resp = client.post("/api/invoices/bulk-edit", json=body, headers=admin_headers())
        assert resp.status_code == 200

    def test_get_invoice_summary(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(return_value=[{"status": "paid", "total": 100.0}, {"status": "sent", "total": 200.0}])
        monkeypatch.setattr("routes.invoices._sql", mock_sql)
        resp = client.get("/api/invoices/summary", headers=admin_headers())
        print("Summary status:", resp.status_code, "body:", resp.text[:200])
        assert resp.status_code == 200

    def test_overdue_count(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(return_value=[{"id": "inv1", "due_date": 1000000}])
        monkeypatch.setattr("routes.invoices._sql", mock_sql)
        resp = client.get("/api/invoices/overdue-count", headers=admin_headers())
        assert resp.status_code == 200

    def test_line_items(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(return_value=[{"id": "li1", "description": "Service", "quantity": 1, "unit_price": 100}])
        monkeypatch.setattr("routes.invoices._sql", mock_sql)
        resp = client.get("/api/invoices/inv1/line-items", headers=admin_headers())
        assert resp.status_code == 200

    def test_add_line_item(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.invoices._call", mock_call)
        monkeypatch.setattr("routes.invoices._log_audit", AsyncMock())
        body = {"description": "Extra item", "quantity": 1, "unit_price": 50}
        resp = client.post("/api/invoices/inv1/line-items", json=body, headers=admin_headers())
        assert resp.status_code == 200

    def test_delete_line_item(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.invoices._call", mock_call)
        monkeypatch.setattr("routes.invoices._log_audit", AsyncMock())
        resp = client.delete("/api/invoices/inv1/line-items/li1", headers=admin_headers())
        assert resp.status_code == 200

    def test_delete_invoice(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.invoices._call", mock_call)
        monkeypatch.setattr("routes.invoices._log_audit", AsyncMock())
        resp = client.delete("/api/invoices/inv1", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_update_tax_rate(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.invoices._call", mock_call)
        monkeypatch.setattr("routes.invoices._log_audit", AsyncMock())
        body = {"tax_rate": 8.5}
        resp = client.put("/api/invoices/inv1/tax-rate", json=body, headers=admin_headers())
        assert resp.status_code == 200

    def test_get_invoice_pdf(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [{"id": "inv1", "number": "INV-001", "status": "sent", "total": 100, "customer_id": "c1"}],
            [],
            [{"first_name": "John", "last_name": "Doe"}],
        ])
        monkeypatch.setattr("routes.invoices._sql", mock_sql)
        async def _fake_pdf(html): return b"%PDF-1.4 fake pdf content"
        monkeypatch.setattr("routes.invoices.html_to_pdf", _fake_pdf)
        resp = client.get("/api/invoices/inv1/pdf", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"

    def test_trigger_overdue_check(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.invoices._call", mock_call)
        monkeypatch.setattr("routes.invoices._log_audit", AsyncMock())
        resp = client.post("/api/invoices/trigger-overdue-check", headers=admin_headers())
        assert resp.status_code == 200

    def test_send_overdue_reminders(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(return_value=[])
        monkeypatch.setattr("routes.invoices._sql", mock_sql)
        monkeypatch.setattr("routes.invoices._log_audit", AsyncMock())
        resp = client.post("/api/invoices/send-overdue-reminders", headers=admin_headers())
        assert resp.status_code == 200

    def test_send_email(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(side_effect=[
            [{"id": "inv1", "customer_id": "c1", "number": "INV-001", "total": 100}],
            [{"email": "cust@example.com"}],
        ])
        monkeypatch.setattr("routes.invoices._sql", mock_sql)
        monkeypatch.setattr("routes.invoices._notify_invoice_created", lambda *a, **kw: None)
        monkeypatch.setattr("routes.invoices._log_audit", AsyncMock())
        body = {"invoice_id": "inv1"}
        resp = client.post("/api/invoices/send-email", json=body, headers=admin_headers())
        assert resp.status_code == 200

    def test_email_queue_status(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(return_value=([{"id": "e1", "status": "sent"}], 1))
        monkeypatch.setattr("routes.invoices._paginated", mock_sql)
        resp = client.get("/api/invoices/email-queue-status", headers=admin_headers())
        assert resp.status_code == 200
