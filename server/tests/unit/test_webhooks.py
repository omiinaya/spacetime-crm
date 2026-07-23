"""Unit tests for server/webhooks.py.

Tests HMAC-SHA256 signing, webhook delivery with retries,
and event firing logic with subscription matching.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class TestSignPayload:
    """HMAC-SHA256 signing."""

    def test_sign_payload(self) -> None:
        from webhooks import _sign_payload

        payload = b'{"event": "test"}'
        sig = _sign_payload(payload, "my-secret")
        assert sig != ""
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA256 hex digest is 64 chars

    def test_sign_empty_secret_returns_empty(self) -> None:
        from webhooks import _sign_payload

        sig = _sign_payload(b"data", "")
        assert sig == ""

    def test_sign_different_secrets_different_signatures(self) -> None:
        from webhooks import _sign_payload

        payload = b'the same payload'
        sig1 = _sign_payload(payload, "secret-1")
        sig2 = _sign_payload(payload, "secret-2")
        assert sig1 != sig2

    def test_sign_different_payloads_different_signatures(self) -> None:
        from webhooks import _sign_payload

        sig1 = _sign_payload(b"payload-a", "secret")
        sig2 = _sign_payload(b"payload-b", "secret")
        assert sig1 != sig2

    def test_sign_consistent(self) -> None:
        """Same payload + secret should produce the same signature."""
        from webhooks import _sign_payload

        sig1 = _sign_payload(b"consistent data", "my-secret")
        sig2 = _sign_payload(b"consistent data", "my-secret")
        assert sig1 == sig2


class TestDeliver:
    """Webhook delivery with retry logic."""

    @pytest.mark.asyncio
    async def test_successful_delivery(self) -> None:
        """Should return ok=True for 2xx responses."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("webhooks.get_http_client", return_value=mock_client):
            from webhooks import _deliver

            result = await _deliver("https://example.com/hook", "test.event", {"key": "val"}, "secret")

        assert result["ok"] is True
        assert result["status_code"] == 200
        assert result["attempt"] == 1

    @pytest.mark.asyncio
    async def test_delivery_sends_correct_headers(self) -> None:
        """Should include signature, event type, and user-agent headers."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("webhooks.get_http_client", return_value=mock_client):
            from webhooks import _deliver

            await _deliver("https://example.com/hook", "ticket.created", {"id": "t-1"}, "sec-123")

        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["headers"]["Content-Type"] == "application/json"
        assert call_kwargs["headers"]["X-Webhook-Event"] == "ticket.created"
        assert call_kwargs["headers"]["X-Webhook-Signature"] != ""
        assert call_kwargs["headers"]["User-Agent"] == "SpacetimeCRM-Webhook/1.0"

    @pytest.mark.asyncio
    async def test_client_error_no_retry(self) -> None:
        """Should not retry on 4xx client errors."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("webhooks.get_http_client", return_value=mock_client):
            from webhooks import _deliver

            result = await _deliver("https://example.com/hook", "test.event", {}, "secret", max_retries=3)

        assert result["ok"] is False
        assert result["status_code"] == 400
        assert result["attempt"] == 1  # Only 1 attempt — no retry on 4xx

    @pytest.mark.asyncio
    async def test_server_error_retries(self) -> None:
        """Should retry on 5xx server errors with exponential backoff."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("webhooks.get_http_client", return_value=mock_client):
            from webhooks import _deliver

            result = await _deliver("https://example.com/hook", "test.event", {}, "secret", max_retries=2)

        assert result["ok"] is False
        assert result["attempt"] == 2  # Retried once after first failure
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_timeout_retries(self) -> None:
        """Should retry on timeout."""
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("webhooks.get_http_client", return_value=mock_client):
            from webhooks import _deliver

            result = await _deliver("https://example.com/hook", "test.event", {}, "secret", max_retries=2)

        assert result["ok"] is False
        assert result["attempt"] == 2
        assert "timeout" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_request_error_retries(self) -> None:
        """Should retry on httpx request errors."""
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        with patch("webhooks.get_http_client", return_value=mock_client):
            from webhooks import _deliver

            result = await _deliver("https://example.com/hook", "test.event", {}, "secret", max_retries=2)

        assert result["ok"] is False
        assert result["attempt"] == 2

    @pytest.mark.asyncio
    async def test_success_on_retry(self) -> None:
        """Should return success if a retry succeeds."""
        mock_client = MagicMock()
        mock_resp_ok = MagicMock()
        mock_resp_ok.status_code = 200
        mock_resp_err = MagicMock()
        mock_resp_err.status_code = 500
        mock_client.post = AsyncMock(side_effect=[mock_resp_err, mock_resp_ok])

        with patch("webhooks.get_http_client", return_value=mock_client):
            from webhooks import _deliver

            result = await _deliver("https://example.com/hook", "test.event", {}, "secret", max_retries=2)

        assert result["ok"] is True
        assert result["attempt"] == 2
        assert result["status_code"] == 200


class TestFireEvent:
    """Event dispatch to matching subscriptions."""

    @pytest.fixture
    def subscriptions(self) -> list[dict]:
        return [
            {"id": "wh-1", "url": "https://hooks.example.com/1", "events": "customer.created,ticket.created", "secret": "sec-1", "active": True},
            {"id": "wh-2", "url": "https://hooks.example.com/2", "events": "invoice.created", "secret": "sec-2", "active": True},
            {"id": "wh-3", "url": "https://hooks.example.com/3", "events": "customer.created", "secret": "sec-3", "active": False},
        ]

    @pytest.mark.asyncio
    async def test_fires_only_matching_active_subscriptions(self, subscriptions) -> None:
        """Should fire only to active subscriptions that subscribe to the event."""
        from webhooks import fire_event

        with patch("webhooks._deliver", new_callable=AsyncMock) as mock_deliver:
            mock_deliver.return_value = {"ok": True, "status_code": 200, "attempt": 1, "error": None}
            results = await fire_event("customer.created", {"id": "c-1"}, subscriptions)

        # Should fire to wh-1 (active, matches) but not wh-2 (no match) or wh-3 (inactive)
        assert len(results) == 1
        assert results[0]["subscription_id"] == "wh-1"

    @pytest.mark.asyncio
    async def test_fires_no_subscriptions_when_no_match(self, subscriptions) -> None:
        """Should return empty list when no subscription matches the event."""
        from webhooks import fire_event

        with patch("webhooks._deliver", new_callable=AsyncMock) as mock_deliver:
            results = await fire_event("unknown.event", {"id": "x"}, subscriptions)

        assert results == []
        mock_deliver.assert_not_called()

    @pytest.mark.asyncio
    async def test_fires_multiple_matching_subscriptions(self) -> None:
        """Should fire to all active subscriptions that match the event."""
        subs = [
            {"id": "wh-a", "url": "https://a.com/hook", "events": "ticket.created", "secret": "s1", "active": True},
            {"id": "wh-b", "url": "https://b.com/hook", "events": "ticket.created", "secret": "s2", "active": True},
        ]

        from webhooks import fire_event

        with patch("webhooks._deliver", new_callable=AsyncMock) as mock_deliver:
            mock_deliver.return_value = {"ok": True, "status_code": 200, "attempt": 1, "error": None}
            results = await fire_event("ticket.created", {"id": "t-1"}, subs)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_inactive_subscription_skipped(self) -> None:
        """Should skip inactive subscriptions."""
        subs = [
            {"id": "wh-inactive", "url": "https://x.com/hook", "events": "test.event", "secret": "s", "active": False},
        ]

        from webhooks import fire_event

        with patch("webhooks._deliver", new_callable=AsyncMock) as mock_deliver:
            results = await fire_event("test.event", {"id": "x"}, subs)

        assert results == []
        mock_deliver.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_subscription_list(self) -> None:
        """Should return empty list when no subscriptions provided."""
        from webhooks import fire_event

        with patch("webhooks._deliver", new_callable=AsyncMock) as mock_deliver:
            results = await fire_event("test.event", {"id": "x"}, [])
        assert results == []
        mock_deliver.assert_not_called()

    @pytest.mark.asyncio
    async def test_logs_failed_delivery(self, subscriptions) -> None:
        """Should log a warning when delivery fails."""
        from webhooks import fire_event

        with patch("webhooks._deliver", new_callable=AsyncMock) as mock_deliver:
            mock_deliver.return_value = {"ok": False, "status_code": 500, "attempt": 3, "error": "HTTP 500"}
            with patch("webhooks.logger") as mock_logger:
                results = await fire_event("customer.created", {"id": "c-1"}, subscriptions)

        assert len(results) == 1
        assert results[0]["ok"] is False
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_deliver_result_includes_subscription_id_and_url(self) -> None:
        """Delivery result should include subscription_id and url."""
        subs = [
            {"id": "wh-1", "url": "https://example.com/hook", "events": "test.event", "secret": "s", "active": True},
        ]

        from webhooks import fire_event

        with patch("webhooks._deliver", new_callable=AsyncMock) as mock_deliver:
            mock_deliver.return_value = {"ok": True, "status_code": 200, "attempt": 1, "error": None}
            results = await fire_event("test.event", {"hello": "world"}, subs)

        assert results[0]["subscription_id"] == "wh-1"
        assert results[0]["url"] == "https://example.com/hook"

    @pytest.mark.asyncio
    async def test_event_constants(self) -> None:
        """All event type constants should be defined and in ALL_EVENTS."""
        from webhooks import ALL_EVENTS, EVENT_CUSTOMER_CREATED, EVENT_CUSTOMER_UPDATED

        assert EVENT_CUSTOMER_CREATED in ALL_EVENTS
        assert EVENT_CUSTOMER_UPDATED in ALL_EVENTS
