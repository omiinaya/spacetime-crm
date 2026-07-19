"""Webhook routes: Stripe webhook, subscription CRUD, and test delivery."""
import httpx
import pytest
from .conftest import SERVER_URL, assert_ok, unique_suffix, _stdb_sql, _track_entity


def _create_webhook(auth_headers: dict, suffix: str = "") -> str:
    """Create a webhook subscription and return its ID.

    Uses a unique URL and STDB SQL lookup for test isolation.
    """
    suf = suffix or unique_suffix()
    url = f"https://example-{suf}.com/webhook"
    resp = httpx.post(
        f"{SERVER_URL}/api/webhook-subscriptions",
        json={"url": url, "events": "customer.created,ticket.created", "secret": "test-secret"},
        headers=auth_headers, timeout=10,
    )
    assert_ok(resp)

    # Look up by unique URL to avoid picking up data from other tests
    rows = _stdb_sql(f"SELECT id FROM webhook_subscription WHERE url = '{url}'")
    assert len(rows) >= 1, f"No webhook found with URL '{url}'"
    wid = rows[0]["id"]
    _track_entity("webhook_subscription", wid)
    return wid


class TestWebhookCRUD:
    """Webhook subscription create, list, update, delete."""

    def test_create(self, auth_headers: dict, session_suffix: str):
        url = f"https://hooks-{session_suffix}-{unique_suffix()}.example.com/crm"
        resp = httpx.post(
            f"{SERVER_URL}/api/webhook-subscriptions",
            json={"url": url, "events": "customer.created,invoice.paid", "secret": "whsec_abc123"},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_create_missing_url(self, auth_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/webhook-subscriptions", json={"events": "customer.created"}, headers=auth_headers, timeout=10)
        assert resp.status_code == 422

    def test_create_invalid_events(self, auth_headers: dict):
        resp = httpx.post(
            f"{SERVER_URL}/api/webhook-subscriptions",
            json={"url": "https://example.com/hook", "events": "nonexistent.event"},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 400

    def test_list(self, auth_headers: dict):
        # Create one first so list is non-empty
        _create_webhook(auth_headers, "list")
        resp = httpx.get(f"{SERVER_URL}/api/webhook-subscriptions", headers=auth_headers, timeout=10)
        data = assert_ok(resp)
        assert "subscriptions" in data
        assert "total" in data

    def test_update(self, auth_headers: dict):
        sub_id = _create_webhook(auth_headers, "update")
        resp = httpx.put(
            f"{SERVER_URL}/api/webhook-subscriptions/{sub_id}",
            json={"url": "https://updated.example.com/hook", "events": "ticket.updated", "secret": "new-secret", "active": False},
            headers=auth_headers, timeout=10,
        )
        assert_ok(resp)

    def test_update_invalid_events(self, auth_headers: dict):
        sub_id = _create_webhook(auth_headers, "inv")
        resp = httpx.put(
            f"{SERVER_URL}/api/webhook-subscriptions/{sub_id}",
            json={"url": "https://example.com/hook", "events": "made.up.event", "secret": "", "active": True},
            headers=auth_headers, timeout=10,
        )
        assert resp.status_code == 400

    def test_delete(self, auth_headers: dict):
        sub_id = _create_webhook(auth_headers, "delete")
        resp = httpx.delete(f"{SERVER_URL}/api/webhook-subscriptions/{sub_id}", headers=auth_headers, timeout=10)
        assert_ok(resp)

    def test_delete_nonexistent(self, auth_headers: dict):
        resp = httpx.delete(f"{SERVER_URL}/api/webhook-subscriptions/nonexistent-999", headers=auth_headers, timeout=10)
        assert resp.status_code < 500


class TestWebhookTest:
    """Test delivery endpoint."""

    def test_test_endpoint(self, auth_headers: dict):
        """Test endpoint should attempt delivery (may fail, that's ok)."""
        sub_id = _create_webhook(auth_headers, "test")
        resp = httpx.post(f"{SERVER_URL}/api/webhook-subscriptions/{sub_id}/test", headers=auth_headers, timeout=10)
        # The delivery attempt might fail or succeed depending on network
        assert resp.status_code < 500, f"Test endpoint returned {resp.status_code}: {resp.text[:200]}"

    def test_test_nonexistent(self, auth_headers: dict):
        resp = httpx.post(f"{SERVER_URL}/api/webhook-subscriptions/nonexistent-999/test", headers=auth_headers, timeout=10)
        assert resp.status_code == 404


class TestWebhookStripe:
    """Stripe webhook endpoint (signature verification)."""

    def test_stripe_webhook_no_signature(self, auth_headers: dict):
        """Without a valid stripe signature, should return 400."""
        resp = httpx.post(f"{SERVER_URL}/api/webhooks/stripe", json={"type": "checkout.session.completed", "data": {"object": {}}}, headers=auth_headers, timeout=10)
        assert resp.status_code == 400


class TestWebhookErrors:
    """Auth enforcement for webhook subscriptions."""

    def test_unauthorized_list(self, client: httpx.Client):
        resp = client.get("/api/webhook-subscriptions", timeout=10)
        assert resp.status_code in (401, 403)

    def test_unauthorized_create(self, client: httpx.Client):
        resp = client.post("/api/webhook-subscriptions", json={"url": "https://example.com", "events": "customer.created"}, timeout=10)
        assert resp.status_code in (401, 403)
