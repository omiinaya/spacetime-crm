"""Unit tests for webhook routes (subscriptions)."""

from unittest.mock import AsyncMock


def admin_headers():
    import jwt

    from config import settings

    token = jwt.encode(
        {"sub": "user-1", "tenant_id": "t1", "role": "admin"}, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    return {"Authorization": f"Bearer {token}"}


class TestWebhooks:
    def test_list_subscriptions(self, client, monkeypatch) -> None:
        mock_ws = AsyncMock(
            side_effect=[
                [{"id": "ws1", "url": "http://example.com/hook"}],  # subscription
                [],  # events
            ]
        )
        monkeypatch.setattr("routes.webhooks._get_webhook_subscriptions", mock_ws)
        resp = client.get("/api/webhook-subscriptions", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_create_subscription(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.webhooks._call", mock_call)
        monkeypatch.setattr("routes.webhooks._log_audit", AsyncMock())
        body = {"url": "http://example.com/hook", "events": "customer.created", "secret": ""}
        resp = client.post("/api/webhook-subscriptions", json=body, headers=admin_headers())
        assert resp.status_code == 200

    def test_update_subscription(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.webhooks._call", mock_call)
        monkeypatch.setattr("routes.webhooks._log_audit", AsyncMock())
        body = {"url": "http://example.com/hook", "events": "customer.created", "secret": "", "active": True}
        resp = client.put("/api/webhook-subscriptions/ws1", json=body, headers=admin_headers())
        assert resp.status_code == 200

    def test_delete_subscription(self, client, monkeypatch) -> None:
        mock_call = AsyncMock(return_value={})
        monkeypatch.setattr("routes.webhooks._call", mock_call)
        monkeypatch.setattr("routes.webhooks._log_audit", AsyncMock())
        resp = client.delete("/api/webhook-subscriptions/ws1", headers=admin_headers())
        assert resp.status_code == 200

    def test_test_subscription(self, client, monkeypatch) -> None:
        mock_sql = AsyncMock(return_value=[{"id": "ws1", "url": "http://example.com/hook", "secret": ""}])
        monkeypatch.setattr("routes.webhooks._sql", mock_sql)
        monkeypatch.setattr("routes.webhooks._deliver", AsyncMock(return_value={"ok": True}))
        resp = client.post("/api/webhook-subscriptions/ws1/test", headers=admin_headers())
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
