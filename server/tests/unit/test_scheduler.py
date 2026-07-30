"""Unit tests for server/scheduler.py.

Tests the _http() singleton and each scheduled task function.
httpx.AsyncClient calls are mocked to avoid requiring a running server.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


@pytest.fixture(autouse=True)
def _reset_client():
    """Reset the global _client between tests."""
    import scheduler

    scheduler._client = None
    yield
    scheduler._client = None


class TestHttpClient:
    """_http() singleton client."""

    def test_returns_async_client(self) -> None:
        """Should return an httpx.AsyncClient instance."""
        from scheduler import _http

        client = _http()
        assert isinstance(client, httpx.AsyncClient)

    def test_returns_singleton(self) -> None:
        """Subsequent calls should return the same client."""
        from scheduler import _http

        client1 = _http()
        client2 = _http()
        assert client1 is client2

    def test_uses_correct_base_url(self) -> None:
        """Should be configured with localhost:8723."""
        from scheduler import _http

        client = _http()
        assert client._base_url.host == "localhost"
        assert client._base_url.port == 8723

    def test_sets_timeout(self) -> None:
        """Should have a 30s timeout with 5s connect timeout."""
        from scheduler import _http

        client = _http()
        assert client._timeout.connect == 5.0

    def test_reset_creates_new_client(self) -> None:
        """Resetting _client should create a new instance on next call."""
        import scheduler

        client1 = scheduler._http()
        scheduler._client = None
        client2 = scheduler._http()
        assert client1 is not client2


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

        mock_logger.warning.assert_any_call(
            "[scheduler:appointments] send-reminders returned 404"
        )


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

        mock_logger.warning.assert_any_call(
            "[scheduler:lowstock] 5 low-stock products detected"
        )

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


class TestScheduledTasksConfig:
    """SCHEDULED_TASKS dictionary."""

    def test_contains_all_five_tasks(self) -> None:
        """Should define all five scheduled tasks."""
        from scheduler import SCHEDULED_TASKS

        assert "overdue_check" in SCHEDULED_TASKS
        assert "recurring_invoices" in SCHEDULED_TASKS
        assert "appointment_reminders" in SCHEDULED_TASKS
        assert "low_stock_alerts" in SCHEDULED_TASKS
        assert "log_cleanup" in SCHEDULED_TASKS

    def test_correct_intervals(self) -> None:
        """Should have the documented intervals."""
        from scheduler import SCHEDULED_TASKS

        assert SCHEDULED_TASKS["overdue_check"][1] == 3600
        assert SCHEDULED_TASKS["recurring_invoices"][1] == 86400
        assert SCHEDULED_TASKS["appointment_reminders"][1] == 3600
        assert SCHEDULED_TASKS["low_stock_alerts"][1] == 3600
        assert SCHEDULED_TASKS["log_cleanup"][1] == 86400

    def test_each_task_is_callable(self) -> None:
        """Each task entry should be a (coroutine_function, interval) tuple."""
        import asyncio as _asyncio

        from scheduler import SCHEDULED_TASKS

        for name, (func, interval) in SCHEDULED_TASKS.items():
            assert _asyncio.iscoroutinefunction(func), (
                f"{name} is not a coroutine function"
            )
            assert isinstance(interval, int), f"{name} interval is not an int"


# ===================================================================
# Exception handling coverage
# ===================================================================


class TestOverdueCheckExceptions(BaseSchedulerTest):
    """Additional exception handling for overdue_check."""

    def test_trigger_overdue_check_non_200(self) -> None:
        """Should log warning when trigger-overdue-check returns non-200."""
        from scheduler import overdue_check

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
                    asyncio.run(overdue_check(0))

        mock_logger.warning.assert_any_call(
            "[scheduler:overdue] trigger-overdue-check returned 500"
        )

    def test_send_overdue_reminders_non_200(self) -> None:
        """Should log warning when send-overdue-reminders returns non-200."""
        from scheduler import overdue_check

        mock_client = MagicMock()
        mock_client.post = AsyncMock()

        # First call (trigger-overdue-check) returns 200, second (send-reminders) returns 404
        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.json.return_value = {"overdue_count": 0, "overdue_total": 0.0}
        resp_err = MagicMock()
        resp_err.status_code = 404
        mock_client.post.side_effect = [resp_ok, resp_err]

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(overdue_check(0))

        mock_logger.warning.assert_any_call(
            "[scheduler:overdue] send-overdue-reminders returned 404"
        )

    def test_general_exception(self) -> None:
        """Should catch and log general exceptions without crashing."""
        from scheduler import overdue_check

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=ValueError("Unexpected error"))

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(overdue_check(0))

        mock_logger.error.assert_called()


class TestRecurringInvoicesExceptions(BaseSchedulerTest):
    """Additional exception handling for recurring_invoices."""

    def test_general_exception(self) -> None:
        """Should catch and log general exceptions without crashing."""
        from scheduler import recurring_invoices

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=ValueError("Unexpected error"))

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(recurring_invoices(0))

        mock_logger.error.assert_called()


class TestAppointmentRemindersExceptions(BaseSchedulerTest):
    """Additional exception handling for appointment_reminders."""

    def test_general_exception(self) -> None:
        """Should catch and log general exceptions without crashing."""
        from scheduler import appointment_reminders

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=ValueError("Unexpected error"))

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(appointment_reminders(0))

        mock_logger.error.assert_called()


class TestLowStockAlertsExceptions(BaseSchedulerTest):
    """Additional exception handling for low_stock_alerts."""

    def test_non_200_response(self) -> None:
        """Should log debug when low-stock endpoint returns non-200."""
        from scheduler import low_stock_alerts

        mock_client = MagicMock()
        mock_client.get = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client.get.return_value = mock_resp

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(low_stock_alerts(0))

        mock_logger.debug.assert_any_call(
            "[scheduler:lowstock] No low-stock endpoint or empty"
        )

    def test_general_exception(self) -> None:
        """Should catch and log general exceptions without crashing."""
        from scheduler import low_stock_alerts

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=ValueError("Unexpected error"))

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(low_stock_alerts(0))

        mock_logger.error.assert_called()


class TestLogCleanupExceptions(BaseSchedulerTest):
    """Additional exception handling for log_cleanup."""

    def test_general_exception(self) -> None:
        """Should catch and log general exceptions without crashing."""
        from scheduler import log_cleanup

        mock_client = MagicMock()
        mock_client.delete = AsyncMock(side_effect=ValueError("Unexpected error"))

        mock_http = MagicMock(return_value=mock_client)
        mock_sleep = AsyncMock()
        mock_sleep.side_effect = [None, asyncio.CancelledError()]

        with patch("scheduler._http", mock_http):
            with patch("scheduler.asyncio.sleep", mock_sleep):
                with patch("scheduler.logger") as mock_logger:
                    asyncio.run(log_cleanup(0))

        mock_logger.error.assert_called()
