"""Unit tests for scheduler.log_cleanup task."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from .base import BaseSchedulerTest


class TestLogCleanup(BaseSchedulerTest):
    """log_cleanup task."""

    def test_calls_cleanup_endpoint(self) -> None:
        """Should DELETE audit-logs/cleanup?days=90."""
        from scheduler import log_cleanup

        self._run_and_expect(
            log_cleanup,
            0,
            "/api/audit-logs/cleanup?days=90",
            "DELETE",
            mock_json={"deleted": 42},
        )

    def test_logs_deleted_count(self) -> None:
        """Should log how many entries were deleted."""
        from scheduler import log_cleanup

        mock_client = MagicMock()
        mock_client.delete = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"deleted": 42}
        mock_client.delete.return_value = mock_resp

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(log_cleanup(0))

        mock_logger.info.assert_any_call(
            "[scheduler:cleanup] Archived 42 old audit log entries"
        )

    def test_handles_connect_error(self) -> None:
        """Should not crash on ConnectError."""
        from scheduler import log_cleanup

        mock_client = MagicMock()
        mock_client.delete = AsyncMock(side_effect=httpx.ConnectError("refused"))

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                asyncio.run(log_cleanup(0))

    def test_handles_cancelled_error(self) -> None:
        """Should exit cleanly on CancelledError."""
        from scheduler import log_cleanup

        mock_client = MagicMock()
        mock_client.delete = AsyncMock()

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = asyncio.CancelledError()

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                asyncio.run(log_cleanup(0))

    def test_handles_non_200_response(self) -> None:
        """Should handle non-200 responses."""
        from scheduler import log_cleanup

        mock_client = MagicMock()
        mock_client.delete = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client.delete.return_value = mock_resp

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(log_cleanup(0))

        mock_logger.debug.assert_any_call(
            "[scheduler:cleanup] No cleanup endpoint or empty"
        )

    def test_uses_90_days(self) -> None:
        """Should query with days=90."""
        from scheduler import log_cleanup

        mock_client = MagicMock()
        mock_client.delete = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"deleted": 0}
        mock_client.delete.return_value = mock_resp

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger"):
                    asyncio.run(log_cleanup(0))

        mock_client.delete.assert_awaited_with("/api/audit-logs/cleanup?days=90")
