"""Tests for helpers module (core STDB helpers, auth middleware, SQL sanitization).

These are unit tests with mocked HTTP clients and JWT decoding.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from helpers import (
    _safe_customer,
    _sanitize_sql,
    _safe_id,
    _sort,
    CUSTOMER_SENSITIVE_FIELDS,
    STATUS_LABELS,
    STATUS_CSS,
    security,
    TEMPLATE_DIR,
)


class TestConstants:
    def test_customer_sensitive_fields(self):
        assert "portal_password_hash" in CUSTOMER_SENSITIVE_FIELDS

    def test_status_labels(self):
        assert STATUS_LABELS["draft"] == "Draft"
        assert STATUS_LABELS["paid"] == "Paid"

    def test_status_css(self):
        assert STATUS_CSS["overdue"] == "overdue"

    def test_template_dir_exists(self):
        assert TEMPLATE_DIR.name == "templates"

    def test_security_scheme(self):
        assert security.scheme_name is not None


class TestSafeCustomer:
    def test_strips_sensitive_fields(self):
        customer = {
            "id": "c_1",
            "first_name": "John",
            "email": "j@b.com",
            "portal_password_hash": "abc123",
        }
        result = _safe_customer(customer)
        assert "portal_password_hash" not in result
        assert result["first_name"] == "John"

    def test_preserves_all_other_fields(self):
        customer = {"id": "c_1", "name": "John", "phone": "555-1234"}
        result = _safe_customer(customer)
        assert result == customer


class TestSanitizeSql:
    def test_escapes_single_quote(self):
        assert _sanitize_sql("O'Brien") == "O''Brien"

    def test_returns_safe_string_unchanged(self):
        assert _sanitize_sql("hello") == "hello"

    def test_handles_empty_string(self):
        assert _sanitize_sql("") == ""

    def test_preserves_special_chars(self):
        assert _sanitize_sql("user@example.com") == "user@example.com"


class TestSafeId:
    def test_accepts_valid_id(self):
        assert _safe_id("usr_abc123") == "usr_abc123"

    def test_accepts_id_with_dashes(self):
        assert _safe_id("tnt-abc-def") == "tnt-abc-def"

    def test_raises_on_empty_string(self):
        with pytest.raises(HTTPException) as exc:
            _safe_id("")
        assert exc.value.status_code == 400

    def test_raises_on_special_chars(self):
        with pytest.raises(HTTPException) as exc:
            _safe_id("'; DROP TABLE user; --")
        assert exc.value.status_code == 400

    def test_accepts_alphanumeric_only(self):
        assert _safe_id("abc123") == "abc123"


class TestSort:
    def test_sorts_desc_by_default(self):
        rows = [{"name": "Beta"}, {"name": "Alpha"}, {"name": "Gamma"}]
        result = _sort(rows, "name")
        assert result[0]["name"] == "Gamma"
        assert result[-1]["name"] == "Alpha"

    def test_sorts_ascending(self):
        rows = [{"name": "Beta"}, {"name": "Alpha"}, {"name": "Gamma"}]
        result = _sort(rows, "name", desc=False)
        assert result[0]["name"] == "Alpha"
        assert result[-1]["name"] == "Gamma"

    def test_handles_none_values(self):
        rows = [{"name": "Beta"}, {"name": None}, {"name": "Alpha"}]
        result = _sort(rows, "name")
        # None values get sorted to one end
        assert len(result) == 3

    def test_sorts_by_numeric_key(self):
        rows = [{"order": 3}, {"order": 1}, {"order": 2}]
        result = _sort(rows, "order", desc=False)
        assert result[0]["order"] == 1
        assert result[-1]["order"] == 3


class TestSqlHelper:
    @pytest.mark.asyncio
    async def test_executes_sql_and_parses_response(self):
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "rows": [["u1", "admin"], ["u2", "tech"]],
                "schema": {
                    "elements": [
                        {"name": {"some": "id"}},
                        {"name": {"some": "role"}},
                    ]
                },
            }
        ]
        mock_client.post.return_value = mock_response

        with patch("helpers.get_http_client", return_value=mock_client):
            with patch("helpers.settings") as mock_settings:
                mock_settings.stdb_sql_url = "http://localhost:3001/v1/database/spacetime-crm/sql"
                from helpers import _sql

                result = await _sql("SELECT * FROM user")

        assert len(result) == 2
        assert result[0]["id"] == "u1"
        assert result[0]["role"] == "admin"
        assert result[1]["id"] == "u2"

    @pytest.mark.asyncio
    async def test_raises_on_sql_error(self):
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_client.post.return_value = mock_response

        with patch("helpers.get_http_client", return_value=mock_client):
            with patch("helpers.settings") as mock_settings:
                mock_settings.stdb_sql_url = "http://localhost:3001/v1/database/spacetime-crm/sql"
                from helpers import _sql

                with pytest.raises(HTTPException) as exc:
                    await _sql("SELECT * FROM bad_table")
                assert exc.value.status_code == 502

    @pytest.mark.asyncio
    async def test_handles_empty_response(self):
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_client.post.return_value = mock_response

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _sql

            result = await _sql("SELECT * FROM empty")
            assert result == []


class TestSqlTHelper:
    @pytest.mark.asyncio
    async def test_appends_tenant_filter_to_where(self):
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = [{"id": "x"}]
            from helpers import _sql_t

            await _sql_t("SELECT * FROM invoices WHERE status = 'sent'", "tnt_abc")

            # Should inject AND tenant_id before end of query
            called_query = mock_sql.call_args[0][0]
            assert "tenant_id = 'tnt_abc'" in called_query
            assert "AND tenant_id" in called_query

    @pytest.mark.asyncio
    async def test_adds_where_clause_when_missing(self):
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = [{"id": "x"}]
            from helpers import _sql_t

            await _sql_t("SELECT * FROM invoices", "tnt_abc")

            called_query = mock_sql.call_args[0][0]
            assert "WHERE tenant_id = 'tnt_abc'" in called_query

    @pytest.mark.asyncio
    async def test_bypasses_tenant_for_empty_tenant_id(self):
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = []
            from helpers import _sql_t

            await _sql_t("SELECT * FROM invoices", "")

            called_query = mock_sql.call_args[0][0]
            assert "tenant_id" not in called_query

    @pytest.mark.asyncio
    async def test_rejects_invalid_tenant_id(self):
        from helpers import _sql_t

        with pytest.raises(HTTPException) as exc:
            await _sql_t("SELECT * FROM invoices", "bad-id'; DROP TABLE user;--")
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_inserts_before_order_by(self):
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = []
            from helpers import _sql_t

            await _sql_t("SELECT * FROM invoices ORDER BY created_at DESC", "tnt_1")

            called_query = mock_sql.call_args[0][0]
            idx_where = called_query.find("WHERE")
            idx_order = called_query.find("ORDER BY")
            assert idx_where < idx_order
            assert "tenant_id = 'tnt_1'" in called_query

    @pytest.mark.asyncio
    async def test_inserts_before_limit(self):
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = []
            from helpers import _sql_t

            await _sql_t("SELECT * FROM invoices LIMIT 10", "tnt_1")

            called_query = mock_sql.call_args[0][0]
            idx_where = called_query.find("WHERE")
            idx_limit = called_query.find("LIMIT")
            assert idx_where < idx_limit
            assert "tenant_id = 'tnt_1'" in called_query

    @pytest.mark.asyncio
    async def test_inserts_where_before_order_by_when_no_where(self):
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = []
            from helpers import _sql_t

            await _sql_t("SELECT * FROM invoices ORDER BY id", "tnt_1")

            called_query = mock_sql.call_args[0][0]
            assert "WHERE tenant_id = 'tnt_1'" in called_query
            idx_where = called_query.find("WHERE")
            idx_order = called_query.find("ORDER BY")
            assert idx_where < idx_order


class TestCallHelper:
    @pytest.mark.asyncio
    async def test_calls_reducer_and_returns_json(self):
        mock_client = AsyncMock()
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_client.post.return_value = mock_resp

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _call

            result = await _call("create_ticket", ["c1", "Broken"])

        assert result == {"ok": True}
        url_arg = mock_client.post.call_args[0][0]
        assert "create_ticket" in url_arg

    @pytest.mark.asyncio
    async def test_raises_on_error(self):
        mock_client = AsyncMock()
        mock_resp = Mock()
        mock_resp.status_code = 502
        mock_resp.text = "Bad gateway"
        mock_client.post.return_value = mock_resp

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _call

            with pytest.raises(HTTPException) as exc:
                await _call("bad_reducer")
            assert exc.value.status_code == 502

    @pytest.mark.asyncio
    async def test_returns_default_on_no_json(self):
        mock_client = AsyncMock()
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_client.post.return_value = mock_resp

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _call

            result = await _call("test")
            assert result == {"ok": True}


class TestLogAudit:
    @pytest.mark.asyncio
    async def test_calls_log_audit_reducer(self):
        user = {"tenant_id": "tnt_1", "id": "u_1", "name": "Admin"}
        with patch("helpers._call", new_callable=AsyncMock) as mock_call:
            from helpers import _log_audit

            await _log_audit(user, "update", "ticket", "t_42", "Updated status")

        mock_call.assert_called_once_with(
            "log_audit",
            ["tnt_1", "u_1", "Admin", "update", "ticket", "t_42", "Updated status"],
        )

    @pytest.mark.asyncio
    async def test_never_raises_on_error(self):
        from helpers import _log_audit

        with patch("helpers._call", new_callable=AsyncMock, side_effect=Exception("DB down")):
            # Should not raise
            await _log_audit({"tenant_id": "t", "id": "u", "name": "N"}, "test", "e", "id")


class TestPaginated:
    @pytest.mark.asyncio
    async def test_returns_paginated_rows(self):
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            # First call is count, second call is data
            mock_sql.side_effect = [
                [{"cnt": 3}],
                [
                    {"id": "t_1", "name": "Alpha", "created_at": "2024-01-01"},
                    {"id": "t_2", "name": "Beta", "created_at": "2024-01-02"},
                    {"id": "t_3", "name": "Gamma", "created_at": "2024-01-03"},
                ],
            ]
            from helpers import _paginated

            rows, total = await _paginated("tnt_1", "ticket", offset=0, limit=2)

        assert total == 3
        assert len(rows) == 2

    @pytest.mark.asyncio
    async def test_strips_sensitive_fields(self):
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.side_effect = [
                [{"cnt": 1}],
                [{"id": "c_1", "name": "John", "portal_password_hash": "abc"}],
            ]
            from helpers import _paginated

            rows, total = await _paginated("tnt_1", "customer", sensitive_fields={"portal_password_hash"})

        assert "portal_password_hash" not in rows[0]

    @pytest.mark.asyncio
    async def test_default_order_by_created_at_desc(self):
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.side_effect = [
                [{"cnt": 3}],
                [
                    {"id": "3", "created_at": "2024-01-03"},
                    {"id": "1", "created_at": "2024-01-01"},
                    {"id": "2", "created_at": "2024-01-02"},
                ],
            ]
            from helpers import _paginated

            rows, total = await _paginated("tnt_1", "ticket")
            # Should be sorted desc by created_at
            assert rows[0]["id"] == "3"
            assert rows[-1]["id"] == "1"


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_raises_without_credentials(self):
        from helpers import get_current_user

        # When Depends returns None, the function should get credentials=None
        with pytest.raises(HTTPException) as exc:
            await get_current_user(None)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_raises_on_expired_token(self):
        mock_creds = Mock(spec=HTTPAuthorizationCredentials)
        mock_creds.credentials = "expired.jwt.here"

        with patch("helpers.jwt.decode", side_effect=__import__("jwt").ExpiredSignatureError()):
            from helpers import get_current_user

            with pytest.raises(HTTPException) as exc:
                await get_current_user(mock_creds)
            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        mock_creds = Mock(spec=HTTPAuthorizationCredentials)
        mock_creds.credentials = "valid.jwt.here"

        with patch("helpers.jwt.decode", return_value={"sub": "u_1", "tenant_id": "tnt_1"}):
            with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
                mock_sql.return_value = [{"id": "u_1", "name": "Admin", "role": "admin", "active": True}]
                from helpers import get_current_user

                user = await get_current_user(mock_creds)

        assert user["id"] == "u_1"
        assert user["tenant_id"] == "tnt_1"

    @pytest.mark.asyncio
    async def test_raises_when_user_disabled(self):
        mock_creds = Mock(spec=HTTPAuthorizationCredentials)
        mock_creds.credentials = "valid.jwt"

        with patch("helpers.jwt.decode", return_value={"sub": "u_1", "tenant_id": "tnt_1"}):
            with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
                mock_sql.return_value = [{"id": "u_1", "active": False}]
                from helpers import get_current_user

                with pytest.raises(HTTPException) as exc:
                    await get_current_user(mock_creds)
                assert exc.value.status_code == 403


class TestRequireRole:
    @pytest.mark.asyncio
    async def test_allows_admin_for_admin_role(self):
        mock_creds = Mock(spec=HTTPAuthorizationCredentials)
        mock_creds.credentials = "admin.jwt"

        with patch("helpers.jwt.decode", return_value={"sub": "u_1", "tenant_id": "tnt_1"}):
            with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
                mock_sql.return_value = [{"id": "u_1", "role": "admin", "active": True}]
                from helpers import require_role

                check = require_role("admin", "tech")  # noqa: F841
                # The dependency returns a callable; calling it returns the user
                user = await check(mock_creds)
                assert user["role"] == "admin"

    @pytest.mark.asyncio
    async def test_blocks_wrong_role(self):
        mock_creds = Mock(spec=HTTPAuthorizationCredentials)
        mock_creds.credentials = "tech.jwt"

        with patch("helpers.jwt.decode", return_value={"sub": "u_1", "tenant_id": "tnt_1"}):
            with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
                mock_sql.return_value = [{"id": "u_1", "role": "front_desk", "active": True}]
                from helpers import require_role

                check = require_role("admin", "tech")
                with pytest.raises(HTTPException) as exc:
                    await check(mock_creds)
                assert exc.value.status_code == 403
