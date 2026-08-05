"""Tests for handlers module (FastAPI exception handler registration)."""

import json
from unittest.mock import Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from handlers import register_exception_handlers


class TestRegisterExceptionHandlers:
    def test_registers_all_handlers(self):
        app = FastAPI()
        register_exception_handlers(app)
        assert RequestValidationError in app.exception_handlers
        assert HTTPException in app.exception_handlers
        assert Exception in app.exception_handlers
        assert ValidationError in app.exception_handlers


class TestValidationErrorHandler:
    @pytest.mark.asyncio
    async def test_returns_422_json_with_field_errors(self):
        app = FastAPI()
        register_exception_handlers(app)
        errors = [
            {"loc": ["body", "email"], "msg": "field required", "type": "value_error.missing"},
        ]
        exc = RequestValidationError(errors)
        handler = app.exception_handlers[RequestValidationError]
        request = Mock()
        request.method = "POST"
        request.url.path = "/test"

        response = await handler(request, exc)
        assert response.status_code == 422
        data = json.loads(response.body)
        assert data["detail"] == "Validation Error"
        assert len(data["errors"]) == 1
        assert data["errors"][0]["field"] == "body.email"
        assert data["errors"][0]["message"] == "field required"

    @pytest.mark.asyncio
    async def test_handles_multiple_errors(self):
        app = FastAPI()
        register_exception_handlers(app)
        errors = [
            {"loc": ["body", "email"], "msg": "field required", "type": "value_error.missing"},
            {"loc": ["body", "name"], "msg": "field required", "type": "value_error.missing"},
        ]
        exc = RequestValidationError(errors)
        handler = app.exception_handlers[RequestValidationError]
        request = Mock()
        response = await handler(request, exc)
        data = json.loads(response.body)
        assert len(data["errors"]) == 2


class TestHTTPExceptionHandler:
    @pytest.mark.asyncio
    async def test_returns_json_with_status_and_detail(self):
        app = FastAPI()
        register_exception_handlers(app)
        exc = HTTPException(status_code=404, detail="Not found")
        handler = app.exception_handlers[HTTPException]
        request = Mock()
        response = await handler(request, exc)
        assert response.status_code == 404
        data = json.loads(response.body)
        assert data["detail"] == "Not found"

    @pytest.mark.asyncio
    async def test_preserves_headers(self):
        app = FastAPI()
        register_exception_handlers(app)
        exc = HTTPException(status_code=429, detail="Rate limited", headers={"Retry-After": "60"})
        handler = app.exception_handlers[HTTPException]
        request = Mock()
        response = await handler(request, exc)
        assert response.status_code == 429
        assert response.headers.get("Retry-After") == "60"


class TestUnhandledExceptionHandler:
    @pytest.mark.asyncio
    async def test_returns_500_json_without_stack_leak(self):
        app = FastAPI()
        register_exception_handlers(app)
        exc = RuntimeError("something broke")
        handler = app.exception_handlers[Exception]
        request = Mock()
        request.method = "GET"
        request.url.path = "/api/test"
        response = await handler(request, exc)
        assert response.status_code == 500
        data = json.loads(response.body)
        assert data["detail"] == "Internal server error"


class TestPydanticValidationHandler:
    @pytest.mark.asyncio
    async def test_returns_422_for_pydantic_validation_error(self):
        app = FastAPI()
        register_exception_handlers(app)
        from pydantic import BaseModel, Field

        class _TestModel(BaseModel):
            name: str = Field(min_length=1)

        with pytest.raises(ValidationError):
            _TestModel(name="")
