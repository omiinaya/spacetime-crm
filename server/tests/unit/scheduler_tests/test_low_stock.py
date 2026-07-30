"""Unit tests for scheduler.low_stock_alerts task."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from .base import BaseSchedulerTest


class TestLowStockAlerts(BaseSchedulerTest):
    """low_stock_alerts task."""

    def test_calls_low_stock_endpoint(self) -> None:
        """Should GET products/low-stock."""
        from scheduler import low_stock_alerts

        self._run_and_expect(
            low_stock_alerts,
            0,
            "/api/products/low-stock",
            "GET",
            mock_json=[],
        )

    def test_logs_low_stock_products(self) -> None:
        """Should log each low-stock product when response is a list."""
        from scheduler import low_stock_alerts

        mock_client = MagicMock()
        mock_client.get = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"name": "Widget", "id": "p-1", "quantity_on_hand": 2},
            {"name": "Gadget", "id": "p-2", "quantity_on_hand": 0},
        ]
        mock_client.get.return_value = mock_resp

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(low_stock_alerts(0))

        assert mock_logger.warning.call_count >= 2
        mock_logger.warning.assert_any_call(
            "[scheduler:lowstock] Low stock: Widget (id=p-1) — 2 remaining"
        )
        mock_logger.warning.assert_any_call(
            "[scheduler:lowstock] Low stock: Gadget (id=p-2) — 0 remaining"
        )

    def test_logs_count_when_response_is_dict(self) -> None:
        """Should log count when response is a dict with count."""
        from scheduler import low_stock_alerts

        mock_client = MagicMock()
        mock_client.get = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"count": 5}
        mock_client.get.return_value = mock_resp

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(low_stock_alerts(0))

        mock_logger.warning.assert_any_call("[scheduler:lowstock] 5 low-stock products detected")

    def test_handles_connect_error(self) -> None:
        """Should not crash on ConnectError."""
        from scheduler import low_stock_alerts

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                asyncio.run(low_stock_alerts(0))

    def test_handles_cancelled_error(self) -> None:
        """Should exit cleanly on CancelledError."""
        from scheduler import low_stock_alerts

        mock_client = MagicMock()
        mock_client.get = AsyncMock()

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = asyncio.CancelledError()

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                asyncio.run(low_stock_alerts(0))

    def test_handles_empty_response(self) -> None:
        """Should handle empty product list."""
        from scheduler import low_stock_alerts

        mock_client = MagicMock()
        mock_client.get = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_client.get.return_value = mock_resp

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger"):
                    asyncio.run(low_stock_alerts(0))
