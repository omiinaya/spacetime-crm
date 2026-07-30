"""Unit tests for helpers._get_webhook_subscriptions and _fire_webhook."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

# ===================================================================
# _get_webhook_subscriptions
# ===================================================================


class TestGetWebhookSubscriptions:
    """Fetch webhook subscriptions from STDB."""

    @pytest.mark.asyncio
    async def test_returns_subscriptions(self) -> None:
        """Should call _sql and return results."""
        expected = [{"id": "wh-1"}, {"id": "wh-2"}]

        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = expected
            from helpers import _get_webhook_subscriptions

            result = await _get_webhook_subscriptions()

        mock_sql.assert_called_once_with("SELECT * FROM webhook_subscriptions")
        assert result == expected

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self) -> None:
        """Should return [] if _sql raises."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.side_effect = RuntimeError("STDB down")
            from helpers import _get_webhook_subscriptions

            result = await _get_webhook_subscriptions()
        assert result == []


# ===================================================================
# _fire_webhook
# ===================================================================


class TestFireWebhook:
    """Dispatch webhook events to matching subscriptions."""

    @pytest.mark.asyncio
    async def test_fires_with_subscriptions(self) -> None:
        """Should get subs then fire_event with them."""
        subs = [{"id": "wh-1", "active": True}]

        with (
            patch("helpers._get_webhook_subscriptions", new_callable=AsyncMock) as mock_get,
            patch("helpers._fire_webhook_event", new_callable=AsyncMock) as mock_fire,
        ):
            mock_get.return_value = subs
            from helpers import _fire_webhook

            await _fire_webhook("customer.created", {"id": "c-1"})

        mock_get.assert_called_once()
        mock_fire.assert_called_once_with("customer.created", {"id": "c-1"}, subs)

    @pytest.mark.asyncio
    async def test_skips_if_no_subscriptions(self) -> None:
        """Should not fire_event if no subscriptions found."""
        with (
            patch("helpers._get_webhook_subscriptions", new_callable=AsyncMock) as mock_get,
            patch("helpers._fire_webhook_event", new_callable=AsyncMock) as mock_fire,
        ):
            mock_get.return_value = []
            from helpers import _fire_webhook

            await _fire_webhook("customer.created", {"id": "c-1"})

        mock_get.assert_called_once()
        mock_fire.assert_not_called()

    @pytest.mark.asyncio
    async def test_never_raises(self) -> None:
        """Should swallow exceptions gracefully."""
        with (
            patch("helpers._get_webhook_subscriptions", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.side_effect = RuntimeError("boom")
            from helpers import _fire_webhook

            await _fire_webhook("test.event", {})  # should not raise
        assert True
