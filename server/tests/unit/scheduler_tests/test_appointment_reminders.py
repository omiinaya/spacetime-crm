"""Unit tests for scheduler.appointment_reminders task."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from .base import BaseSchedulerTest


class TestAppointmentReminders(BaseSchedulerTest):
    """appointment_reminders task."""

    def test_calls_send_reminders_endpoint(self) -> None:
        """Should POST to appointments/send-reminders."""
        from scheduler import appointment_reminders

        self._run_and_expect(
            appointment_reminders,
            0,
            "/api/appointments/send-reminders",
            "POST",
            mock_json={"sent": 2},
        )

    def test_logs_sent_count(self) -> None:
        """Should log how many reminders were sent."""
        from scheduler import appointment_reminders

        mock_client = MagicMock()
        mock_client.post = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"sent": 4}
        mock_client.post.return_value = mock_resp

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(appointment_reminders(0))

        mock_logger.info.assert_any_call("[scheduler:appointments] Sent 4 reminders")

    def test_handles_connect_error(self) -> None:
        """Should not crash on ConnectError."""
        from scheduler import appointment_reminders

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                asyncio.run(appointment_reminders(0))

    def test_handles_cancelled_error(self) -> None:
        """Should exit cleanly on CancelledError."""
        from scheduler import appointment_reminders

        mock_client = MagicMock()
        mock_client.post = AsyncMock()

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = asyncio.CancelledError()

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                asyncio.run(appointment_reminders(0))

    def test_handles_non_200_response(self) -> None:
        """Should handle non-200 responses."""
        from scheduler import appointment_reminders

        mock_client = MagicMock()
        mock_client.post = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client.post.return_value = mock_resp

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(appointment_reminders(0))

        mock_logger.warning.assert_any_call("[scheduler:appointments] send-reminders returned 404")
