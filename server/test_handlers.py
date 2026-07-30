"""
Tests for server/handlers.py.

Tests FastAPI exception handler registration and response formatting.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from server.handlers import register_exception_handlers


class TestHandlers:
    """Test suite for handlers.py."""

    def test_register_handlers_registers_four_handlers(self):
        """register_exception_handlers adds 4 exception handlers to the app."""
        from fastapi import HTTPException
        from fastapi.exceptions import RequestValidationError

        app = MagicMock(spec=FastAPI)
        registered = {}

        def mock_exception_handler(exc_class):
            def decorator(func):
                registered[exc_class] = func
                return func

            return decorator

        app.exception_handler = mock_exception_handler
        register_exception_handlers(app)

        assert RequestValidationError in registered
        assert ValidationError in registered
        assert HTTPException in registered
        assert Exception in registered

    @pytest.mark.asyncio
    async def test_validation_error_fields(self):
        """RequestValidationError handler returns 422 with field-level errors."""
        app = FastAPI()
        register_exception_handlers(app)

        mock_request = MagicMock(spec=Request)
        raw_errors = [
            {
                "loc": ("body", "email"),
                "msg": "field required",
                "type": "value_error.missing",
            }
        ]
        exc = RequestValidationError(raw_errors)

        handler = app.exception_handlers.get(RequestValidationError)
        assert handler is not None

        response = await handler(mock_request, exc)
        assert response.status_code == 422
        body = json.loads(response.body)
        assert body["detail"] == "Validation Error"
        assert len(body["errors"]) == 1
        assert body["errors"][0]["field"] == "body.email"

    @pytest.mark.asyncio
    async def test_http_exception_formats_json(self):
        """HTTPException handler returns JSON with status code."""
        app = FastAPI()
        register_exception_handlers(app)

        mock_request = MagicMock(spec=Request)
        exc = HTTPException(status_code=404, detail="Not found")

        handler = app.exception_handlers.get(HTTPException)
        assert handler is not None

        response = await handler(mock_request, exc)
        assert response.status_code == 404
        body = json.loads(response.body)
        assert body["detail"] == "Not found"

    @pytest.mark.asyncio
    async def test_unhandled_exception_returns_500_json(self):
        """Unhandled Exception handler returns 500 JSON without stack traces."""
        app = FastAPI()
        register_exception_handlers(app)

        mock_request = MagicMock(spec=Request)
        mock_request.method = "GET"
        mock_request.url.path = "/test"
        exc = RuntimeError("something broke")

        handler = app.exception_handlers.get(Exception)
        assert handler is not None

        response = await handler(mock_request, exc)
        assert response.status_code == 500
        body = json.loads(response.body)
        assert body["detail"] == "Internal server error"

    @pytest.mark.asyncio
    async def test_pydantic_validation_handler(self):
        """Raw Pydantic ValidationError handler returns 422 JSON."""
        app = FastAPI()
        register_exception_handlers(app)

        mock_request = MagicMock(spec=Request)
        from pydantic import BaseModel, Field

        class TempModel(BaseModel):
            name: str = Field(...)

        with pytest.raises(ValidationError) as exc_info:
            TempModel(name=123)
        exc = exc_info.value

        handler = app.exception_handlers.get(ValidationError)
        assert handler is not None

        response = await handler(mock_request, exc)
        assert response.status_code == 422
        body = json.loads(response.body)
        assert body["detail"] == "Validation Error"
