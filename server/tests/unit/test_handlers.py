"""Unit tests for server/handlers.py.

Tests that exception handlers are registered correctly and return
proper JSON response structures for different exception types.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


class TestRegisterExceptionHandlers:
    """Exception handler registration."""

    def test_registers_four_handlers(self) -> None:
        """Should register handlers for all four exception types."""
        from handlers import register_exception_handlers

        handlers: dict = {}

        class MockApp:
            def exception_handler(self, exc_type):
                def decorator(func):
                    handlers[exc_type] = func
                    return func
                return decorator

        app = MockApp()
        register_exception_handlers(app)

        assert len(handlers) == 4
        assert RequestValidationError in handlers
        assert ValidationError in handlers
        assert HTTPException in handlers
        assert Exception in handlers

    def test_handler_registered_as_decorator(self) -> None:
        """Each handler should be installed as a decorator on the app."""
        from handlers import register_exception_handlers

        call_args = []

        class TrackingApp:
            def exception_handler(self, exc_type):
                def decorator(func):
                    call_args.append((exc_type, func))
                    return func
                return decorator

        app = TrackingApp()
        register_exception_handlers(app)

        registered_types = [t for t, f in call_args]
        assert RequestValidationError in registered_types
        assert ValidationError in registered_types
        assert HTTPException in registered_types
        assert Exception in registered_types


class TestRequestValidationHandler:
    """RequestValidationError → 422 JSON with field-level details."""

    @pytest.fixture
    def _handler(self):
        """Capture the handler function from registration."""
        from handlers import register_exception_handlers

        handlers = {}

        class MockApp:
            def exception_handler(self, exc_type):
                def decorator(func):
                    handlers[exc_type] = func
                    return func
                return decorator

        register_exception_handlers(MockApp())
        return handlers[RequestValidationError]

    @pytest.mark.asyncio
    async def test_returns_422(self, _handler) -> None:
        """Should return 422 status code."""
        request = MagicMock(spec=Request)
        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = []

        response = await _handler(request, exc)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_response_structure(self, _handler) -> None:
        """Should return JSON with detail and errors list."""
        request = MagicMock(spec=Request)
        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = [
            {"loc": ("body", "email"), "msg": "field required", "type": "value_error.missing"},
            {"loc": ("body", "age"), "msg": "Input should be a valid integer", "type": "int_parsing"},
        ]

        response = await _handler(request, exc)
        body = json.loads(response.body)

        assert body["detail"] == "Validation Error"
        assert len(body["errors"]) == 2
        assert body["errors"][0]["field"] == "body.email"
        assert body["errors"][0]["message"] == "field required"
        assert body["errors"][0]["type"] == "value_error.missing"
        assert body["errors"][1]["field"] == "body.age"

    @pytest.mark.asyncio
    async def test_empty_errors(self, _handler) -> None:
        """Should handle empty error list."""
        request = MagicMock(spec=Request)
        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = []

        response = await _handler(request, exc)
        body = json.loads(response.body)

        assert body["detail"] == "Validation Error"
        assert body["errors"] == []

    @pytest.mark.asyncio
    async def test_uses_errors_method(self, _handler) -> None:
        """Should call exc.errors() to get error details."""
        request = MagicMock(spec=Request)
        exc = MagicMock(spec=RequestValidationError)
        exc.errors.return_value = [{"loc": ("query", "page"), "msg": "Invalid", "type": "value_error"}]

        await _handler(request, exc)
        exc.errors.assert_called_once()


class TestPydanticValidationHandler:
    """Raw Pydantic ValidationError → 422 JSON with field-level details."""

    @pytest.fixture
    def _handler(self):
        from handlers import register_exception_handlers

        handlers = {}

        class MockApp:
            def exception_handler(self, exc_type):
                def decorator(func):
                    handlers[exc_type] = func
                    return func
                return decorator

        register_exception_handlers(MockApp())
        return handlers[ValidationError]

    @pytest.mark.asyncio
    async def test_returns_422(self, _handler) -> None:
        """Should return 422 status code."""
        request = MagicMock(spec=Request)
        exc = MagicMock(spec=ValidationError)
        exc.errors.return_value = []

        response = await _handler(request, exc)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_response_structure(self, _handler) -> None:
        """Should return field-level error details."""
        request = MagicMock(spec=Request)
        exc = MagicMock(spec=ValidationError)
        exc.errors.return_value = [
            {"loc": ("name",), "msg": "Field required", "type": "missing"},
        ]

        response = await _handler(request, exc)
        body = json.loads(response.body)

        assert body["detail"] == "Validation Error"
        assert body["errors"][0]["field"] == "name"
        assert body["errors"][0]["message"] == "Field required"

    @pytest.mark.asyncio
    async def test_empty_errors(self, _handler) -> None:
        """Should handle empty errors gracefully."""
        request = MagicMock(spec=Request)
        exc = MagicMock(spec=ValidationError)
        exc.errors.return_value = []

        response = await _handler(request, exc)
        body = json.loads(response.body)
        assert body["errors"] == []


class TestHTTPExceptionHandler:
    """HTTPException → JSON response matching the status code."""

    @pytest.fixture
    def _handler(self):
        from handlers import register_exception_handlers

        handlers = {}

        class MockApp:
            def exception_handler(self, exc_type):
                def decorator(func):
                    handlers[exc_type] = func
                    return func
                return decorator

        register_exception_handlers(MockApp())
        return handlers[HTTPException]

    @pytest.mark.asyncio
    async def test_404_response(self, _handler) -> None:
        """Should return 404 JSON when HTTPException has status_code 404."""
        request = MagicMock(spec=Request)
        exc = HTTPException(status_code=404, detail="Not found")

        response = await _handler(request, exc)

        assert response.status_code == 404
        body = json.loads(response.body)
        assert body["detail"] == "Not found"

    @pytest.mark.asyncio
    async def test_401_response(self, _handler) -> None:
        """Should return 401 JSON."""
        request = MagicMock(spec=Request)
        exc = HTTPException(status_code=401, detail="Unauthorized")

        response = await _handler(request, exc)

        assert response.status_code == 401
        body = json.loads(response.body)
        assert body["detail"] == "Unauthorized"

    @pytest.mark.asyncio
    async def test_403_response(self, _handler) -> None:
        """Should return 403 JSON."""
        request = MagicMock(spec=Request)
        exc = HTTPException(status_code=403, detail="Forbidden")

        response = await _handler(request, exc)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_500_response(self, _handler) -> None:
        """Should return 500 JSON for server errors."""
        request = MagicMock(spec=Request)
        exc = HTTPException(status_code=500, detail="Internal server error")

        response = await _handler(request, exc)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_includes_headers(self, _handler) -> None:
        """Should forward headers from the exception."""
        request = MagicMock(spec=Request)
        exc = HTTPException(status_code=429, detail="Too Many Requests", headers={"Retry-After": "120"})

        response = await _handler(request, exc)

        assert response.status_code == 429
        assert response.headers.get("Retry-After") == "120"

    @pytest.mark.asyncio
    async def test_no_headers_when_none(self, _handler) -> None:
        """Should handle missing headers gracefully."""
        request = MagicMock(spec=Request)
        exc = HTTPException(status_code=400, detail="Bad request")

        response = await _handler(request, exc)
        # JSONResponse adds Content-Type, but no custom headers
        custom_headers = {k: v for k, v in response.headers.items() if k.lower() != "content-type"}
        assert not custom_headers or "retry-after" not in {k.lower() for k in response.headers}


class TestUnhandledExceptionHandler:
    """Generic Exception → 500 JSON without stack trace leakage."""

    @pytest.fixture
    def _handler(self):
        from handlers import register_exception_handlers

        handlers = {}

        class MockApp:
            def exception_handler(self, exc_type):
                def decorator(func):
                    handlers[exc_type] = func
                    return func
                return decorator

        register_exception_handlers(MockApp())
        return handlers[Exception]

    @pytest.mark.asyncio
    async def test_returns_500(self, _handler) -> None:
        """Should return 500 status code."""
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/test"
        exc = RuntimeError("Something broke")

        response = await _handler(request, exc)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_no_stack_trace_in_response(self, _handler) -> None:
        """Should not leak stack traces to the client."""
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/test"
        exc = RuntimeError("Something broke")

        response = await _handler(request, exc)
        body = json.loads(response.body)

        assert body["detail"] == "Internal server error"
        # Sanity check: the actual error message should NOT appear in the response
        assert "Something broke" not in response.body.decode()

    @pytest.mark.asyncio
    async def test_logs_error(self, _handler) -> None:
        """Should log the exception server-side."""
        from handlers import logger

        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/orders"
        exc = ValueError("Invalid order data")

        with pytest.MonkeyPatch.context() as mp:
            log_messages = []

            def fake_error(msg, *args, **kwargs):
                log_messages.append(msg % args if args else msg)

            mp.setattr(logger, "error", fake_error)
            await _handler(request, exc)

        # The logger.error should have been called with traceback info
        assert any("Unhandled exception" in msg for msg in log_messages)
        assert any("POST" in msg for msg in log_messages)
        assert any("/api/orders" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_different_http_methods(self, _handler) -> None:
        """Should log the correct method and path regardless of HTTP verb."""
        from handlers import logger

        for method in ("GET", "POST", "PUT", "DELETE"):
            request = MagicMock(spec=Request)
            request.method = method
            request.url.path = f"/api/{method.lower()}"
            exc = Exception("Test error")

            with pytest.MonkeyPatch.context() as mp:
                log_messages = []

                def fake_error(msg, *args, **kwargs):
                    log_messages.append(msg % args if args else msg)

                mp.setattr(logger, "error", fake_error)
                await _handler(request, exc)

            assert any(method in msg for msg in log_messages)
