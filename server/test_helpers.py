"""
Tests for server/helpers.py.

Tests STDB helpers, auth middleware, and shared utilities.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from server.helpers import (
    CUSTOMER_SENSITIVE_FIELDS,
    STATUS_CSS,
    STATUS_LABELS,
    _call,
    _log_audit,
    _paginated,
    _safe_customer,
    _safe_id,
    _sort,
    _sql,
    _sql_t,
    require_role,
)


class TestHelpers:
    """Test suite for helpers.py."""

    def test_safe_customer_strips_sensitive_fields(self):
        customer = {"id": "c1", "name": "Test", "portal_password_hash": "secret"}
        result = _safe_customer(customer)
        assert "portal_password_hash" not in result
        assert result["id"] == "c1"
        assert result["name"] == "Test"

    def test_safe_customer_preserves_other_fields(self):
        customer = {"id": "c1", "email": "a@b.com", "phone": "555"}
        result = _safe_customer(customer)
        assert result == customer

    def test_status_labels_defined(self):
        for key in ("draft", "sent", "paid", "partial", "overdue", "cancelled"):
            assert key in STATUS_LABELS

    def test_status_css_defined(self):
        for key in ("draft", "sent", "paid", "partial", "overdue", "cancelled"):
            assert key in STATUS_CSS

    def test_sensitive_fields_set(self):
        assert "portal_password_hash" in CUSTOMER_SENSITIVE_FIELDS

    def test_safe_id_valid(self):
        assert _safe_id("usr_123abc") == "usr_123abc"
        assert _safe_id("abc-123_def") == "abc-123_def"

    def test_safe_id_invalid(self):
        with pytest.raises(HTTPException) as exc:
            _safe_id("")
        assert exc.value.status_code == 400
        with pytest.raises(HTTPException) as exc:
            _safe_id("drop tables")
        assert exc.value.status_code == 400

    def test_sort_by_key_desc(self):
        rows = [{"name": "alpha"}, {"name": "gamma"}, {"name": "beta"}]
        result = _sort(rows, "name")
        assert result[0]["name"] == "gamma"
        assert result[1]["name"] == "beta"
        assert result[2]["name"] == "alpha"

    def test_sort_by_key_asc(self):
        rows = [{"name": "alpha"}, {"name": "gamma"}, {"name": "beta"}]
        result = _sort(rows, "name", desc=False)
        assert result[0]["name"] == "alpha"
        assert result[1]["name"] == "beta"
        assert result[2]["name"] == "gamma"

    def test_sort_handles_none(self):
        rows = [{"name": None}, {"name": "a"}, {"name": None}]
        result = _sort(rows, "name")
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_sql_error_raises_502(self):
        mock_client = AsyncMock()
        mock_resp = MagicMock(spec=["status_code", "text"])
        mock_resp.status_code = 500
        mock_resp.text = "Internal error"
        mock_client.post.return_value = mock_resp
        with patch("server.helpers.get_http_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc:
                await _sql("SELECT * FROM test")
            assert exc.value.status_code == 502

    @pytest.mark.asyncio
    async def test_sql_success_returns_rows(self):
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                "rows": [["1", "Alice"], ["2", "Bob"]],
                "schema": {
                    "elements": [
                        {"name": {"some": "id"}},
                        {"name": {"some": "name"}},
                    ]
                },
            }
        ]
        mock_client.post.return_value = mock_resp
        with patch("server.helpers.get_http_client", return_value=mock_client):
            result = await _sql("SELECT * FROM test")
            assert len(result) == 2
            assert result[0]["id"] == "1"
            assert result[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_call_error_raises_502(self):
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Reducer failed"
        mock_client.post.return_value = mock_resp
        with patch("server.helpers.get_http_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc:
                await _call("test_reducer")
            assert exc.value.status_code == 502

    @pytest.mark.asyncio
    async def test_call_success(self):
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_client.post.return_value = mock_resp
        with patch("server.helpers.get_http_client", return_value=mock_client):
            result = await _call("test_reducer", ["arg1"])
            assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_call_empty_response(self):
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("no json")
        mock_client.post.return_value = mock_resp
        with patch("server.helpers.get_http_client", return_value=mock_client):
            result = await _call("test_reducer")
            assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_log_audit_never_raises(self):
        with patch("server.helpers._call", side_effect=Exception("DB down")):
            result = await _log_audit(
                {"tenant_id": "t1", "id": "u1", "name": "admin"},
                "update",
                "customer",
                "c1",
                "details",
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_log_audit_calls_call(self):
        with patch("server.helpers._call", new_callable=AsyncMock) as mock_call:
            await _log_audit(
                {"tenant_id": "t1", "id": "u1", "name": "admin"},
                "update",
                "customer",
                "c1",
                "details",
            )
            mock_call.assert_called_once_with(
                "log_audit",
                ["t1", "u1", "admin", "update", "customer", "c1", "details"],
            )

    @pytest.mark.asyncio
    async def test_sql_t_adds_tenant_filter(self):
        mock_sql = AsyncMock(return_value=[{"id": "1"}])
        with patch("server.helpers._sql", mock_sql):
            await _sql_t("SELECT * FROM test", "tenant_abc")
            call_query = mock_sql.call_args[0][0]
            assert "tenant_id = 'tenant_abc'" in call_query

    @pytest.mark.asyncio
    async def test_sql_t_no_tenant_id(self):
        mock_sql = AsyncMock(return_value=[])
        with patch("server.helpers._sql", mock_sql):
            await _sql_t("SELECT * FROM test", "")
            call_query = mock_sql.call_args[0][0]
            assert "tenant_id" not in call_query

    @pytest.mark.asyncio
    async def test_sql_t_invalid_tenant_id(self):
        with pytest.raises(HTTPException) as exc:
            await _sql_t("SELECT * FROM test", "bad!id")
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_paginated_returns_rows_and_total(self):
        mock_sql = AsyncMock()
        mock_sql.side_effect = [
            [{"cnt": 5}],
            [
                {"id": "1", "name": "a", "created_at": "2024-01-01"},
                {"id": "2", "name": "b", "created_at": "2024-01-02"},
            ],
        ]
        with patch("server.helpers._sql", mock_sql):
            rows, total = await _paginated(
                "tenant_abc",
                "test_table",
                offset=0,
                limit=10,
            )
            assert total == 5
            assert len(rows) == 2

    def test_require_role_returns_callable(self):
        dep = require_role("admin", "tech")
        assert callable(dep)
