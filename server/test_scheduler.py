"""
Tests for server/scheduler.py.

Tests background task scheduling and periodic health checks.
"""

from __future__ import annotations

import asyncio

import pytest

from server.scheduler import (
    SCHEDULED_TASKS,
    _http,
    appointment_reminders,
    log_cleanup,
    low_stock_alerts,
    overdue_check,
    recurring_invoices,
)


class TestScheduler:
    """Test suite for scheduler.py."""

    def test_scheduled_tasks_defined(self):
        """SCHEDULED_TASKS has all expected tasks."""
        expected = {
            "overdue_check",
            "recurring_invoices",
            "appointment_reminders",
            "low_stock_alerts",
            "log_cleanup",
        }
        assert set(SCHEDULED_TASKS.keys()) == expected

    def test_scheduled_tasks_have_intervals(self):
        """Each task has a positive interval."""
        for name, (_, interval) in SCHEDULED_TASKS.items():
            assert interval > 0, f"{name} has non-positive interval"

    def test_http_returns_async_client(self):
        """_http returns an httpx.AsyncClient."""
        from httpx import AsyncClient

        client = _http()
        assert isinstance(client, AsyncClient)

    def test_http_singleton(self):
        """_http returns the same client on repeated calls."""
        client1 = _http()
        client2 = _http()
        assert client1 is client2

    def test_http_base_url(self):
        """_http client has the correct base_url."""
        client = _http()
        assert str(client._base_url).rstrip("/") == "http://localhost:8723"

    @pytest.mark.asyncio
    async def test_overdue_check_cancelled(self):
        """overdue_check exits cleanly on CancelledError."""
        task = asyncio.create_task(overdue_check(1))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_recurring_invoices_cancelled(self):
        """recurring_invoices exits cleanly on CancelledError."""
        task = asyncio.create_task(recurring_invoices(1))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_appointment_reminders_cancelled(self):
        """appointment_reminders exits cleanly on CancelledError."""
        task = asyncio.create_task(appointment_reminders(1))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_low_stock_alerts_cancelled(self):
        """low_stock_alerts exits cleanly on CancelledError."""
        task = asyncio.create_task(low_stock_alerts(1))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_log_cleanup_cancelled(self):
        """log_cleanup exits cleanly on CancelledError."""
        task = asyncio.create_task(log_cleanup(1))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
