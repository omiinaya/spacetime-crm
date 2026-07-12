"""Unit tests for server/helpers.py — pure function tests.

These tests mock httpx.AsyncClient to prevent network calls during import.
They test only the sync helper functions and constants.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add server directory to path so we can import server modules
_server_dir = str(Path(__file__).resolve().parent.parent.parent)
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

from unittest.mock import patch, MagicMock, AsyncMock

# Patch httpx.AsyncClient before importing anything from server
with patch("httpx.AsyncClient", return_value=AsyncMock()):
    import pytest
    from fastapi import HTTPException
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from helpers import (
        _sanitize_sql,
        _safe_id,
        _safe_customer,
        STATUS_LABELS,
        STATUS_CSS,
        CUSTOMER_SENSITIVE_FIELDS,
        security,
        TEMPLATE_DIR,
        jinja_env,
        _sql,
        _sql_t,
        _paginated,
        _call,
        _sort,
        _log_audit,
        _get_webhook_subscriptions,
        _fire_webhook,
        require_role,
        get_current_user,
        settings,
    )


# ── Module-level objects ───────────────────────────────────────────


class TestModuleLevel:
    """Tests module-level instantiation — including HTTPBearer at line 13/23."""

    def test_security_is_httpbearer(self):
        """Verify the security dependency is an HTTPBearer instance."""
        assert isinstance(security, HTTPBearer)
        assert security.auto_error is True

    def test_template_dir_exists(self):
        """Verify TEMPLATE_DIR points to the templates directory."""
        assert TEMPLATE_DIR.name == "templates"
        assert TEMPLATE_DIR.is_dir() or str(TEMPLATE_DIR).endswith("templates")

    def test_jinja_env_loaded(self):
        """Verify jinja_env is an Environment instance."""
        from jinja2 import Environment

        assert isinstance(jinja_env, Environment)

    def test_jinja_env_uses_correct_dir(self):
        """Verify jinja template directory matches TEMPLATE_DIR."""
        loader = jinja_env.loader
        assert str(TEMPLATE_DIR) in str(loader.searchpath)


# ── Constants ─────────────────────────────────────────────────────


class TestStatusConstants:
    def test_status_labels_contains_all_keys(self):
        for key in ("draft", "sent", "paid", "partial", "overdue", "cancelled"):
            assert key in STATUS_LABELS

    def test_status_labels_contains_all_labels(self):
        labels = {
            "draft": "Draft",
            "sent": "Sent",
            "paid": "Paid",
            "partial": "Partial",
            "overdue": "Overdue",
            "cancelled": "Cancelled",
        }
        assert STATUS_LABELS == labels

    def test_status_css_contains_all_keys(self):
        for key in ("draft", "sent", "paid", "partial", "overdue", "cancelled"):
            assert key in STATUS_CSS

    def test_status_css_maps_correctly(self):
        expected = {
            "draft": "draft",
            "sent": "sent",
            "paid": "paid",
            "partial": "partial",
            "overdue": "overdue",
            "cancelled": "cancelled",
        }
        assert STATUS_CSS == expected

    def test_customer_sensitive_fields(self):
        assert "portal_password_hash" in CUSTOMER_SENSITIVE_FIELDS
        assert len(CUSTOMER_SENSITIVE_FIELDS) == 1


# ── _safe_customer ────────────────────────────────────────────────


class TestSafeCustomer:
    def test_strips_sensitive_fields(self):
        c = {"id": "1", "name": "Test", "portal_password_hash": "secret"}
        result = _safe_customer(c)
        assert "portal_password_hash" not in result
        assert result == {"id": "1", "name": "Test"}

    def test_preserves_other_fields(self):
        c = {"id": "1", "name": "Test", "email": "a@b.com"}
        assert _safe_customer(c) == c

    def test_empty_dict(self):
        assert _safe_customer({}) == {}

    def test_no_sensitive_fields(self):
        c = {"id": "1", "name": "Test"}
        assert _safe_customer(c) == c

    def test_only_sensitive_fields(self):
        c = {"portal_password_hash": "secret"}
        result = _safe_customer(c)
        assert result == {}
        assert "portal_password_hash" not in result

    def test_sensitive_field_case_sensitive(self):
        """Ensure only exact match is stripped."""
        c = {"PORTAL_PASSWORD_HASH": "secret"}
        assert _safe_customer(c) == c


# ── _sanitize_sql ─────────────────────────────────────────────────


class TestSanitizeSql:
    def test_doubles_single_quotes(self):
        assert _sanitize_sql("O'Brien") == "O''Brien"

    def test_no_quotes_unchanged(self):
        assert _sanitize_sql("hello") == "hello"

    def test_empty_string(self):
        assert _sanitize_sql("") == ""

    def test_multiple_quotes(self):
        assert _sanitize_sql("it's a 'test'") == "it''s a ''test''"

    def test_special_chars_preserved(self):
        assert _sanitize_sql("user@domain.com") == "user@domain.com"
        assert _sanitize_sql("john.doe") == "john.doe"

    def test_unicode_preserved(self):
        assert _sanitize_sql("café") == "café"

    def test_numeric_value(self):
        assert _sanitize_sql("123") == "123"

    def test_whitespace_preserved(self):
        assert _sanitize_sql("hello world") == "hello world"


# ── _safe_id ──────────────────────────────────────────────────────


class TestSafeId:
    def test_valid_alphanumeric(self):
        assert _safe_id("abc123") == "abc123"

    def test_valid_with_underscores_and_dashes(self):
        assert _safe_id("abc-123_def") == "abc-123_def"

    def test_valid_uuid_style(self):
        assert _safe_id("a1b2c3d4-e5f6-7890-abcd-ef1234567890") == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    def test_empty_raises(self):
        with pytest.raises(HTTPException, match="Invalid ID format"):
            _safe_id("")

    def test_sql_injection_raises(self):
        with pytest.raises(HTTPException, match="Invalid ID format"):
            _safe_id("'; DROP TABLE users; --")

    def test_spaces_raises(self):
        with pytest.raises(HTTPException, match="Invalid ID format"):
            _safe_id("abc 123")

    def test_special_chars_raises(self):
        with pytest.raises(HTTPException, match="Invalid ID format"):
            _safe_id("abc@123")

    def test_none_value_raises(self):
        with pytest.raises(HTTPException):
            _safe_id("")

    def test_newlines_raises(self):
        with pytest.raises(HTTPException, match="Invalid ID format"):
            _safe_id("abc\n123")

    def test_semicolons_raises(self):
        with pytest.raises(HTTPException, match="Invalid ID format"):
            _safe_id("abc;123")


# ── _sort (synchronous) ──────────────────────────────────────────


class TestSort:
    def test_sorts_ascending(self):
        data = [{"name": "z"}, {"name": "a"}, {"name": "m"}]
        result = _sort(data, "name", desc=False)
        assert [r["name"] for r in result] == ["a", "m", "z"]

    def test_sorts_descending(self):
        data = [{"name": "a"}, {"name": "z"}, {"name": "m"}]
        result = _sort(data, "name", desc=True)
        assert [r["name"] for r in result] == ["z", "m", "a"]

    def test_sorts_by_missing_key(self):
        data = [{"id": 2}, {"id": 1}]
        result = _sort(data, "name", desc=False)
        assert len(result) == 2
        assert result[0]["id"] == 2


# ── _sql (async, with mocked HTTP) ────────────────────────────────


@pytest.mark.asyncio
async def test_sql_returns_rows():
    from client import get_http_client

    client = get_http_client()
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = [
        {
            "rows": [["v1", "v2"], ["v3", "v4"]],
            "schema": {"elements": [{"name": {"some": "col1"}}, {"name": {"some": "col2"}}]},
        }
    ]
    client.post = AsyncMock(return_value=mock_response)
    result = await _sql("SELECT * FROM test")
    assert result == [{"col1": "v1", "col2": "v2"}, {"col1": "v3", "col2": "v4"}]


@pytest.mark.asyncio
async def test_sql_error_raises_502():
    from client import get_http_client

    client = get_http_client()
    client.post = AsyncMock(return_value=MagicMock(status_code=400, text="Bad query"))
    with pytest.raises(HTTPException) as exc:
        await _sql("SELECT BAD")
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_sql_empty_response():
    from client import get_http_client

    client = get_http_client()
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {}
    client.post = AsyncMock(return_value=mock_response)
    result = await _sql("SELECT * FROM empty")
    assert result == []


@pytest.mark.asyncio
async def test_sql_ignores_bad_schema():
    from client import get_http_client

    client = get_http_client()
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = [
        {
            "rows": [["x"]],
            "schema": {"elements": [{"name": {}}]},
        }
    ]
    client.post = AsyncMock(return_value=mock_response)
    result = await _sql("SELECT * FROM bad_schema")
    assert result == [{}]


# ── _sql_t (async, with tenant filter) ────────────────────────────


@pytest.mark.asyncio
async def test_sql_t_appends_tenant_filter():
    from client import get_http_client

    client = get_http_client()
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = [
        {
            "rows": [["t1"]],
            "schema": {"elements": [{"name": {"some": "id"}}]},
        }
    ]
    client.post = AsyncMock(return_value=mock_response)
    result = await _sql_t("SELECT * FROM items", tenant_id="tenant-123")
    assert len(result) == 1
    call_arg = client.post.call_args.kwargs["content"]
    assert "tenant_id" in call_arg.lower()


@pytest.mark.asyncio
async def test_sql_t_no_tenant_passes_through():
    from client import get_http_client

    client = get_http_client()
    client.post = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: []))
    result = await _sql_t("SELECT * FROM items", tenant_id="")
    assert result == []


@pytest.mark.asyncio
async def test_sql_t_invalid_tenant_raises_400():
    with pytest.raises(HTTPException) as exc:
        await _sql_t("SELECT * FROM items", tenant_id="''; DROP TABLE users")
    assert exc.value.status_code == 400


# ── _call (async, with mocked HTTP) ───────────────────────────────


@pytest.mark.asyncio
async def test_call_success():
    from client import get_http_client

    client = get_http_client()
    client.post = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: {"result": "ok"}))
    result = await _call("my_reducer", [1, 2, 3])
    assert result == {"result": "ok"}
    client.post.assert_called_once()
    args, _ = client.post.call_args
    assert settings.stdb_call_url in str(args[0])


@pytest.mark.asyncio
async def test_call_no_args():
    from client import get_http_client

    client = get_http_client()
    client.post = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: {"result": None}))
    result = await _call("no_arg_reducer")
    assert result == {"result": None}


@pytest.mark.asyncio
async def test_call_error_raises_502():
    from client import get_http_client

    client = get_http_client()
    client.post = AsyncMock(return_value=MagicMock(status_code=500, text="Server Error"))
    with pytest.raises(HTTPException) as exc:
        await _call("fail_reducer")
    assert exc.value.status_code == 502


# ── _paginated (async) ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_paginated_basic():
    from client import get_http_client

    client = get_http_client()
    mock_count = MagicMock(status_code=200)
    mock_count.json.return_value = [{"rows": [[5]], "schema": {"elements": [{"name": {"some": "cnt"}}]}}]
    mock_data = MagicMock(status_code=200)
    mock_data.json.return_value = [
        {
            "rows": [["c", 1], ["a", 2], ["b", 3]],
            "schema": {"elements": [{"name": {"some": "name"}}, {"name": {"some": "val"}}]},
        }
    ]
    client.post = AsyncMock(side_effect=[mock_count, mock_data])
    rows, total = await _paginated("test_table", "tid", offset=0, limit=10, order_by="name", order_desc=False)
    assert total == 5
    assert len(rows) == 3
    assert rows[0]["name"] == "a"
    assert rows[-1]["name"] == "c"


@pytest.mark.asyncio
async def test_paginated_with_sensitive_fields():
    from client import get_http_client

    client = get_http_client()
    mock_count = MagicMock(status_code=200)
    mock_count.json.return_value = [{"rows": [[1]], "schema": {"elements": [{"name": {"some": "cnt"}}]}}]
    mock_data = MagicMock(status_code=200)
    mock_data.json.return_value = [
        {
            "rows": [["a", "secret"]],
            "schema": {"elements": [{"name": {"some": "name"}}, {"name": {"some": "pw"}}]},
        }
    ]
    client.post = AsyncMock(side_effect=[mock_count, mock_data])
    rows, total = await _paginated("test_table", "tid", offset=0, limit=10, sensitive_fields={"pw"})
    assert total == 1
    assert "pw" not in rows[0]
    assert rows[0]["name"] == "a"


# ── _log_audit (async) ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_log_audit_success():
    from client import get_http_client

    client = get_http_client()
    client.post = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: {}))
    await _log_audit(
        {"tenant_id": "t1", "id": "u1", "name": "Alice"}, "create", "invoice", "inv-123", "Created invoice"
    )
    client.post.assert_called_once()


@pytest.mark.asyncio
async def test_log_audit_failure_does_not_raise():
    from client import get_http_client

    client = get_http_client()
    client.post = AsyncMock(side_effect=Exception("Network error"))
    await _log_audit({"tenant_id": "t1", "id": "u1", "name": "Alice"}, "read", "user", "u1", "")


# ── _get_webhook_subscriptions (async) ────────────────────────────


@pytest.mark.asyncio
async def test_get_webhook_subs_success():
    from client import get_http_client

    client = get_http_client()
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = [
        {
            "rows": [["sub1", "url1"]],
            "schema": {"elements": [{"name": {"some": "id"}}, {"name": {"some": "url"}}]},
        }
    ]
    client.post = AsyncMock(return_value=mock_response)
    result = await _get_webhook_subscriptions()
    assert len(result) == 1
    assert result[0]["id"] == "sub1"


@pytest.mark.asyncio
async def test_get_webhook_subs_error_returns_empty():
    from client import get_http_client

    client = get_http_client()
    client.post = AsyncMock(side_effect=Exception("DB error"))
    result = await _get_webhook_subscriptions()
    assert result == []


# ── _fire_webhook (async) ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_fire_webhook_success():
    from client import get_http_client

    client = get_http_client()
    mock_sub_response = MagicMock(status_code=200)
    mock_sub_response.json.return_value = [
        {
            "rows": [["sub1", "http://example.com/hook"]],
            "schema": {"elements": [{"name": {"some": "id"}}, {"name": {"some": "url"}}]},
        }
    ]
    client.post = AsyncMock(return_value=mock_sub_response)
    await _fire_webhook("invoice.created", {"id": "inv-1"})


@pytest.mark.asyncio
async def test_fire_webhook_no_subs():
    from client import get_http_client

    client = get_http_client()
    mock_empty = MagicMock(status_code=200)
    mock_empty.json.return_value = [{"rows": [], "schema": {"elements": []}}]
    client.post = AsyncMock(return_value=mock_empty)
    await _fire_webhook("invoice.created", {"id": "inv-1"})


@pytest.mark.asyncio
async def test_fire_webhook_error_caught():
    from client import get_http_client

    client = get_http_client()
    client.post = AsyncMock(side_effect=Exception("DB error"))
    await _fire_webhook("invoice.created", {"id": "inv-1"})


# ── require_role (sync factory) ───────────────────────────────────


class TestRequireRole:
    def test_require_role_returns_callable(self):
        dep = require_role("admin")
        assert callable(dep)

    def test_require_role_no_credentials_raises_401(self):
        dep = require_role("admin")
        import asyncio

        async def run_test():
            with pytest.raises(HTTPException) as exc:
                await dep(None)
            assert exc.value.status_code == 401

        asyncio.run(run_test())


# ── get_current_user (async) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_no_credentials():
    with pytest.raises(HTTPException) as exc:
        await get_current_user(None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")
    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_expired_token():
    import jwt
    import time
    from config import settings

    expired_token = jwt.encode(
        {"sub": "u1", "exp": int(time.time()) - 3600},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=expired_token)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_no_subject():
    import jwt
    from config import settings

    token = jwt.encode(
        {"tenant_id": "t1"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_not_found():
    import jwt
    from config import settings
    from client import get_http_client

    token = jwt.encode(
        {"sub": "unknown-user", "tenant_id": "t1"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    client = get_http_client()
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = [{"rows": [], "schema": {"elements": []}}]
    client.post = AsyncMock(return_value=mock_response)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_disabled():
    import jwt
    from config import settings
    from client import get_http_client

    token = jwt.encode(
        {"sub": "user-1", "tenant_id": "t1"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    client = get_http_client()
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = [
        {
            "rows": [["user-1", "Test", "admin", False]],
            "schema": {
                "elements": [
                    {"name": {"some": "id"}},
                    {"name": {"some": "name"}},
                    {"name": {"some": "role"}},
                    {"name": {"some": "active"}},
                ]
            },
        }
    ]
    client.post = AsyncMock(return_value=mock_response)
    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_user_success():
    import jwt
    from config import settings
    from client import get_http_client

    token = jwt.encode(
        {"sub": "user-1", "tenant_id": "t1"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    client = get_http_client()
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = [
        {
            "rows": [["user-1", "Test", "admin", True]],
            "schema": {
                "elements": [
                    {"name": {"some": "id"}},
                    {"name": {"some": "name"}},
                    {"name": {"some": "role"}},
                    {"name": {"some": "active"}},
                ]
            },
        }
    ]
    client.post = AsyncMock(return_value=mock_response)
    user = await get_current_user(creds)
    assert user["id"] == "user-1"
    assert user["tenant_id"] == "t1"
