"""Unit tests for scheduler.recurring_invoices task."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from .base import BaseSchedulerTest


class TestRecurringInvoices(BaseSchedulerTest):
    """recurring_invoices task."""

    def test_calls_generate_endpoint(self) -> None:
        """Should POST to recurring-invoices/generate."""
        from scheduler import recurring_invoices

        self._run_and_expect(
            recurring_invoices,
            0,
            "/api/recurring-invoices/generate",
            "POST",
            mock_json={"generated": 3},
        )

    def test_logs_generated_count(self) -> None:
        """Should log how many invoices were generated."""
        from scheduler import recurring_invoices

        mock_client = MagicMock()
        mock_client.post = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"generated": 3}
        mock_client.post.return_value = mock_resp

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(recurring_invoices(0))

        mock_logger.info.assert_any_call("[scheduler:recurring] Generated 3 invoices")

    def test_logs_no_invoices_due(self) -> None:
        """Should log debug when no invoices are due."""
        from scheduler import recurring_invoices

        mock_client = MagicMock()
        mock_client.post = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"generated": 0}
        mock_client.post.return_value = mock_resp

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(recurring_invoices(0))

        mock_logger.debug.assert_any_call(
            "[scheduler:recurring] No invoices due for generation"
        )

    def test_handles_connect_error(self) -> None:
        """Should not crash on ConnectError."""
        from scheduler import recurring_invoices

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                asyncio.run(recurring_invoices(0))

    def test_handles_non_200_response(self) -> None:
        """Should handle non-200 responses without crashing."""
        from scheduler import recurring_invoices

        mock_client = MagicMock()
        mock_client.post = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client.post.return_value = mock_resp

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(recurring_invoices(0))

        mock_logger.warning.assert_any_call(
            "[scheduler:recurring] generate returned 500"
        )
