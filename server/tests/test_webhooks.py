"""Webhook routes: Stripe webhook, subscription CRUD, and test delivery."""

import httpx

from .conftest import (
    SERVER_URL,
    _stdb_sql,
    _track_entity,
    assert_ok,
    unique_suffix,
)


def _create_webhook(test_admin_headers: dict, session_suffix: str = "", suffix: str = "") -> str:
    """Create a webhook subscription and return its ID.

    Uses a unique URL and STDB SQL lookup for test isolation.
    session_suffix ensures cleanup by suffix works across sessions.
    """
    suf = suffix or unique_suffix()
    url = f"https://example-{session_suffix}-{suf}.com/webhook"
    resp = httpx.post(
        f"{SERVER_URL}/api/webhook-subscriptions",
        json={
            "url": url,
            "events": "customer.created,ticket.created",
            "secret": "test-secret",
        },
        headers=test_admin_headers,
        timeout=10,
    )
    assert_ok(resp)

    result = _stdb_sql(f"SELECT id FROM webhook_subscriptions WHERE url = '{url}'")
    assert len(result) == 1, f"Expected 1 table result for webhook '{url}'"
    table = result[0]
    assert table.get("rows") and len(table["rows"]) >= 1, f"No webhook found with URL '{url}'"
    wid = table["rows"][0][0]  # id is first (and only) column
    _track_entity("webhook_subscription", wid)
    return wid


class TestWebhookCRUD:
    """Webhook subscription create, list, update, delete."""

    def test_create(self, test_admin_headers: dict, session_suffix: str):
        url = f"https://hooks-{session_suffix}-{unique_suffix()}.example.com/crm"
        resp = httpx.post(
            f"{SERVER_URL}/api/webhook-subscriptions",
            json={
                "url": url,
                "events": "customer.created,invoice.paid",
                "secret": "whsec_abc123",
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_create_missing_url(self, test_admin_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/webhook-subscriptions",
            json={"events": "customer.created"},
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 422

    def test_create_invalid_events(self, test_admin_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/webhook-subscriptions",
            json={"url": "https://example.com/hook", "events": "nonexistent.event"},
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 400

    def test_list(self, test_admin_headers: dict, session_suffix: str):
        # Create one first so list is non-empty
        _create_webhook(test_admin_headers, session_suffix, "list")
        resp = httpx.get(
            f"{SERVER_URL}/api/webhook-subscriptions",
            headers=test_admin_headers,
            timeout=10,
        )
        data = assert_ok(resp)
        assert "subscriptions" in data
        assert "total" in data

    def test_update(self, test_admin_headers: dict, session_suffix: str):
        sub_id = _create_webhook(test_admin_headers, session_suffix, "update")
        resp = httpx.put(
            f"{SERVER_URL}/api/webhook-subscriptions/{sub_id}",
            json={
                "url": "https://updated.example.com/hook",
                "events": "ticket.updated",
                "secret": "new-secret",
                "active": False,
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_update_invalid_events(self, test_admin_headers: dict, session_suffix: str):
        sub_id = _create_webhook(test_admin_headers, session_suffix, "inv")
        resp = httpx.put(
            f"{SERVER_URL}/api/webhook-subscriptions/{sub_id}",
            json={
                "url": "https://example.com/hook",
                "events": "made.up.event",
                "secret": "",
                "active": True,
            },
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 400

    def test_delete(self, test_admin_headers: dict, session_suffix: str):
        sub_id = _create_webhook(test_admin_headers, session_suffix, "delete")
        resp = httpx.delete(
            f"{SERVER_URL}/api/webhook-subscriptions/{sub_id}",
            headers=test_admin_headers,
            timeout=10,
        )
        assert_ok(resp)

    def test_delete_nonexistent(self, test_admin_headers: dict):
        resp = httpx.delete(
            f"{SERVER_URL}/api/webhook-subscriptions/nonexistent-999",
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code < 500


class TestWebhookTest:
    """Test delivery endpoint."""

    def test_test_endpoint(self, test_admin_headers: dict, session_suffix: str):
        """Test endpoint should attempt delivery (may fail, that's ok)."""
        sub_id = _create_webhook(test_admin_headers, session_suffix, "test")
        resp = httpx.post(
            f"{SERVER_URL}/api/webhook-subscriptions/{sub_id}/test",
            headers=test_admin_headers,
            timeout=10,
        )
        # The delivery attempt might fail or succeed depending on network
        assert resp.status_code < 500, f"Test endpoint returned {resp.status_code}: {resp.text[:200]}"

    def test_test_nonexistent(self, test_admin_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/webhook-subscriptions/nonexistent-999/test",
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 404


class TestWebhookStripe:
    """Stripe webhook endpoint (signature verification)."""

    def test_stripe_webhook_no_signature(self, test_admin_headers: dict):
        """Without a valid stripe signature, should return 400."""
        resp = httpx.post(
            f"{SERVER_URL}/api/webhooks/stripe",
            json={"type": "checkout.session.completed", "data": {"object": {}}},
            headers=test_admin_headers,
            timeout=10,
        )
        assert resp.status_code == 400


class TestWebhookErrors:
    """Auth enforcement for webhook subscriptions."""

    def test_unauthorized_list(self, client: httpx.Client):
        resp = client.get("/api/webhook-subscriptions", timeout=10)
        assert resp.status_code in (401, 403)

    def test_unauthorized_create(self, client: httpx.Client):
        resp = client.post(
            "/api/webhook-subscriptions",
            json={"url": "https://example.com", "events": "customer.created"},
            timeout=10,
        )
        assert resp.status_code in (401, 403)
