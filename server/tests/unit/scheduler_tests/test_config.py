"""Unit tests for scheduler.SCHEDULED_TASKS configuration."""

from __future__ import annotations


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
