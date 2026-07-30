"""Unit tests for scheduler.overdue_check task."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from .base import BaseSchedulerTest


class TestOverdueCheck(BaseSchedulerTest):
    """overdue_check task."""

    def test_calls_trigger_overdue_check(self) -> None:
        """Should POST to trigger-overdue-check and send-overdue-reminders."""
        from scheduler import overdue_check

        mock_client = MagicMock()
        mock_client.post = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"overdue_count": 3, "overdue_total": 450.0}
        mock_client.post.return_value = mock_resp

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger"):
                    asyncio.run(overdue_check(0))

        # Both endpoints should have been called
        assert mock_client.post.await_count >= 2
        mock_client.post.assert_any_await("/api/invoices/trigger-overdue-check")
        mock_client.post.assert_any_await("/api/invoices/send-overdue-reminders")

    def test_calls_send_overdue_reminders(self) -> None:
        """Should POST to send-overdue-reminders."""
        from scheduler import overdue_check

        mock_client = self._run_and_expect(
            overdue_check,
            0,
            "/api/invoices/send-overdue-reminders",
            "POST",
            mock_json={"notified": 2},
        )
        mock_client.post.assert_any_await("/api/invoices/send-overdue-reminders")

    def test_handles_connect_error(self) -> None:
        """Should not crash on ConnectError."""
        from scheduler import overdue_check

        mock_client = MagicMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                # Should not raise — ConnectError is caught
                asyncio.run(overdue_check(0))

    def test_handles_cancelled_error(self) -> None:
        """Should exit cleanly on CancelledError."""
        from scheduler import overdue_check

        mock_client = MagicMock()
        mock_client.post = AsyncMock()

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = (
            asyncio.CancelledError()
        )  # CancelledError on first sleep

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                asyncio.run(overdue_check(0))

    def test_logs_overdue_count(self) -> None:
        """Should log the overdue count."""
        from scheduler import overdue_check

        mock_client = MagicMock()
        mock_client.post = AsyncMock()
        mock_resp_ok = MagicMock()
        mock_resp_ok.status_code = 200
        mock_resp_ok.json.return_value = {"overdue_count": 5, "overdue_total": 750.0}
        mock_client.post.return_value = mock_resp_ok

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(overdue_check(0))

        mock_logger.info.assert_any_call(
            "[scheduler:overdue] Check complete: 5 overdue, $750.00 total"
        )
