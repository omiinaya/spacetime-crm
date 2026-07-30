"""Base class and shared fixtures for scheduler unit tests."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_client():
    """Reset the global _client between tests."""
    import scheduler

    scheduler._client = None
    yield
    scheduler._client = None


class BaseSchedulerTest:
    """Common helpers for scheduler task tests."""

    def _run_one_iteration(
        self, task_func, interval: int = 0
    ) -> tuple[AsyncMock, MagicMock]:
        """Run a single iteration of a periodic task by making the second
        asyncio.sleep call raise CancelledError to break the loop.

        Returns (mock_client, mock_sleep) for further assertions.
        """
        mock_client = MagicMock()
        mock_client.post = AsyncMock()
        mock_client.get = AsyncMock()
        mock_client.delete = AsyncMock()

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        # First sleep: let the body execute. Second sleep: break the loop.
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger"):
                    asyncio.run(task_func(interval))

        return mock_client, mock_sleep

    def _run_and_expect(
        self,
        task_func,
        interval: int,
        expected_url: str,
        expected_method: str = "POST",
        mock_status: int = 200,
        mock_json: dict | None = None,
    ) -> AsyncMock:
        """Run one iteration and return the mock client for assertions."""
        mock_client = MagicMock()
        method_mock = AsyncMock()  # will be set on mock_client.{method}
        if expected_method.upper() == "POST":
            mock_client.post = AsyncMock()
            method_mock = mock_client.post
        elif expected_method.upper() == "GET":
            mock_client.get = AsyncMock()
            method_mock = mock_client.get
        elif expected_method.upper() == "DELETE":
            mock_client.delete = AsyncMock()
            method_mock = mock_client.delete

        mock_resp = MagicMock()
        mock_resp.status_code = mock_status
        mock_resp.json.return_value = mock_json or {}
        method_mock.return_value = mock_resp

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        # sleep once (let body run), then CancelledError to break
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger"):
                    asyncio.run(task_func(interval))

        method_mock.assert_awaited_with(expected_url)
        return mock_client
