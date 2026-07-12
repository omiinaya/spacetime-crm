"""Shared utilities for route unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

import jwt
import pytest

from config import settings


def make_token(user_id: str = "user-1", role: str = "admin", tenant_id: str = "t1") -> str:
    """Create a valid JWT token for testing."""
    return jwt.encode(
        {"sub": user_id, "tenant_id": tenant_id, "role": role},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def auth_header(user_id: str = "user-1", role: str = "admin") -> dict:
    """Return Authorization header dict."""
    return {"Authorization": f"Bearer {make_token(user_id=user_id, role=role)}"}


# Mock user returned from require_role dependency
MOCK_USER = {"id": "user-1", "name": "Test User", "role": "admin", "tenant_id": "t1", "active": True}


def mock_stdb_sql_response(rows: list[list], columns: list[str] | None = None) -> list[dict]:
    """Build mock STDB SQL response from rows."""
    if columns is None:
        columns = ["id", "name"]
    schema = {"elements": [{"name": {"some": col}} for col in columns]}
    return [{"rows": rows, "schema": schema}]


def configure_stdb_mock(mock_client, sql_results: list | None = None, call_result: Any = None):
    """Configure the mock STDB client with canned responses."""
    # Default SQL response returns empty
    if sql_results is not None:
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = sql_results
        mock_client.post.return_value = mock_response
    # For call responses
    if call_result is not None:
        call_response = MagicMock(status_code=200)
        call_response.json.return_value = call_result
        mock_client.post.return_value = call_response
