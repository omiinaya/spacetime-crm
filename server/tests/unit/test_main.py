"""Unit tests for server/main.py.

Covers app structure and route registration.
The health endpoint test requires mocking the STDB HTTP client.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import main


class TestAppStructure:
    """The FastAPI app instance with expected configuration."""

    def test_app_title(self) -> None:
        assert main.app.title == "SpacetimeCRM"

    def test_app_has_spa_fallback(self) -> None:
        """The catch-all SPA route is registered."""
        paths = []
        for route in main.app.routes:
            p = getattr(route, "path", None) or (
                getattr(route, "paths", [None])[0] if hasattr(route, "paths") else None
            )
            if p:
                paths.append(p)
        assert any("full_path" in p for p in paths)


class TestHealthEndpoint:
    """The health check endpoint with mocked STDB."""

    async def _mock_stdb_ok(self, url, **kw):
        """Return a mock response that looks like STDB is working."""
        mock = AsyncMock()
        mock.status_code = 200
        return mock

    async def _mock_stdb_fail(self, url, **kw):
        """Return a mock response that looks like STDB is unreachable."""
        raise ConnectionError("STDB not running")

    def test_health_check_returns_ok_when_stdb_up(self) -> None:
        """When STDB is reachable, health returns 200."""
        mock_client = AsyncMock()
        mock_client.post.return_value = AsyncMock(status_code=200)

        with patch("routes.health.get_http_client", return_value=mock_client):
            client = TestClient(main.app)
            resp = client.get("/api/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("server") == "ok"
            assert data.get("stdb") == "ok"

    def test_health_check_returns_json(self) -> None:
        """Health response is valid JSON with expected keys regardless of STDB state."""
        client = TestClient(main.app)
        resp = client.get("/api/health")
        data = resp.json()
        assert set(data.keys()) >= {"server", "stdb", "module"}

    def test_health_ready_returns_unavailable_when_stdb_down(self) -> None:
        """Readiness probe returns unavailable when STDB is not reachable."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = ConnectionError("STDB not running")

        with patch("routes.health.get_http_client", return_value=mock_client):
            client = TestClient(main.app)
            resp = client.get("/api/health/ready")
            assert resp.status_code == 200
            assert resp.json() == {"status": "unavailable"}


class TestLifespan:
    """The lifespan context manager starts and stops scheduler tasks."""

    def test_lifespan_starts_scheduler_tasks(self) -> None:
        """Should create asyncio tasks for each scheduled task on startup."""
        import asyncio

        created_tasks: list[tuple[str, object]] = []

        original_create_task = asyncio.create_task

        def mock_create_task(coro, name=None):
            task = original_create_task(coro, name=name)
            created_tasks.append((name or "", task))
            return task

        # Clear any existing tasks
        original_tasks = list(main._scheduler_tasks)
        main._scheduler_tasks.clear()

        with patch(
            "scheduler.SCHEDULED_TASKS",
            {
                "test_task": (lambda i: asyncio.sleep(0), 100),
            },
        ):
            with patch.object(asyncio, "create_task", mock_create_task):
                with patch("builtins.print"):

                    async def run_lifespan():
                        async with main.lifespan(main.app):
                            pass

                    asyncio.run(run_lifespan())

        # At least one task should have been created
        assert len(created_tasks) >= 1
        assert created_tasks[0][0] == "scheduler:test_task"

        # Restore
        main._scheduler_tasks.clear()
        main._scheduler_tasks.extend(original_tasks)

    def test_lifespan_cancels_tasks_on_shutdown(self) -> None:
        """Should cancel all scheduler tasks on shutdown."""
        import asyncio
        from typing import Any

        cancelled_tasks: list[Any] = []

        class FakeTask:
            def __init__(self):
                self.cancelled = False

            def cancel(self):
                self.cancelled = True
                cancelled_tasks.append(self)

            def done(self):
                return True

        fake_task = FakeTask()
        main._scheduler_tasks.append(fake_task)  # type: ignore[arg-type]

        try:
            with patch("builtins.print"):
                with patch("asyncio.gather", new_callable=AsyncMock) as mock_gather:

                    async def run_lifespan():
                        async with main.lifespan(main.app):
                            pass

                    asyncio.run(run_lifespan())

            assert fake_task.cancelled is True
            mock_gather.assert_awaited_once()
        finally:
            if fake_task in main._scheduler_tasks:
                main._scheduler_tasks.remove(fake_task)


class TestSpaFallback:
    """The SPA fallback route serves index.html or returns 404."""

    def test_returns_not_found_when_index_missing(self) -> None:
        """Should return {'detail': 'Not Found'} when index.html doesn't exist."""
        client = TestClient(main.app)

        # The SPA fallback catches all paths; if index.html doesn't exist
        # in the test environment, it returns {"detail": "Not Found"}
        resp = client.get("/some-nonexistent-page")

        # Either it returns the index.html (200) or {"detail": "Not Found"}
        # depending on whether the web/dist/index.html exists in the test env
        if resp.status_code == 200:
            # If index.html exists, it returns a FileResponse
            assert resp.headers.get("content-type") is not None
        else:
            assert resp.json() == {"detail": "Not Found"}

    def test_returns_not_found_when_static_dir_has_no_index(self) -> None:
        """Should return {'detail': 'Not Found'} when STATIC_DIR has no index.html."""
        import tempfile
        from pathlib import Path

        # Create a temp directory with no index.html
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("main.STATIC_DIR", Path(tmpdir)):
                client = TestClient(main.app)
                resp = client.get("/some-nonexistent-page")
                assert resp.status_code == 200
                assert resp.json() == {"detail": "Not Found"}

    def test_catch_all_route_registered(self) -> None:
        """The catch-all route should be registered on the app."""
        paths = []
        for route in main.app.routes:
            p = getattr(route, "path", None)
            if p:
                paths.append(p)
        # The catch-all route has a path parameter
        assert any("{full_path" in p for p in paths)


class TestModuleStructure:
    """Verify the main module is well-formed."""

    def test_module_docstring(self) -> None:
        """Should have a module docstring."""
        assert main.__doc__ is not None
        assert "FastAPI" in main.__doc__

    def test_scheduler_tasks_list_exists(self) -> None:
        """Should have a _scheduler_tasks list."""
        assert hasattr(main, "_scheduler_tasks")
        assert isinstance(main._scheduler_tasks, list)

    def test_cors_middleware_added(self) -> None:
        """Should have CORS middleware configured."""
        from fastapi.middleware.cors import CORSMiddleware

        # Verify at least one middleware is attached
        assert len(main.app.user_middleware) > 0

        found = False
        for m in main.app.user_middleware:
            if hasattr(m, "cls") and m.cls is CORSMiddleware:
                found = True
                break
        assert found, "CORSMiddleware not found in middleware stack"

    def test_rate_limit_handler_registered(self) -> None:
        """Should have rate limit exception handler registered."""
        from slowapi.errors import RateLimitExceeded

        # Check that the exception handler is registered
        handler = main.app.exception_handlers.get(RateLimitExceeded)
        assert handler is not None
