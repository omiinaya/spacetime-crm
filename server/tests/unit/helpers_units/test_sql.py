"""Unit tests for SQL-related helpers: _sql, _sql_t, _paginated, _call, _sort."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

# ===================================================================
# _sql
# ===================================================================


class TestSql:
    """STDB SQL query execution via get_http_client()."""

    @pytest.mark.asyncio
    async def test_successful_query(self) -> None:
        """Should POST query, parse STDB response, return list of dicts."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                "rows": [["u-1", "Alice"], ["u-2", "Bob"]],
                "schema": {
                    "elements": [
                        {"name": {"some": "id"}},
                        {"name": {"some": "name"}},
                    ]
                },
            }
        ]
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _sql

            result = await _sql("SELECT id, name FROM user")

        assert len(result) == 2
        assert result[0] == {"id": "u-1", "name": "Alice"}
        assert result[1] == {"id": "u-2", "name": "Bob"}

        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["headers"]["Content-Type"] == "application/sql"

    @pytest.mark.asyncio
    async def test_sql_error_raises_502(self) -> None:
        """Should raise HTTPException(502) on >=400 status."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal server error"
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _sql

            with pytest.raises(HTTPException) as exc:
                await _sql("SELECT * FROM bad_table")
            assert exc.value.status_code == 502
            assert "SQL query failed" in exc.value.detail

    @pytest.mark.asyncio
    async def test_handles_empty_response(self) -> None:
        """Should handle empty/malformed STDB response gracefully."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _sql

            result = await _sql("SELECT * FROM empty_table")
        assert result == []

    @pytest.mark.asyncio
    async def test_handles_no_schema_elements(self) -> None:
        """Should handle rows without schema elements field."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"rows": [["v1"]], "schema": {"elements": [{"name": {}}]}}]
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _sql

            result = await _sql("SELECT count(*) FROM t")
        assert result == [{}]

    @pytest.mark.asyncio
    async def test_response_is_not_list(self) -> None:
        """Should return empty list when response is not a list."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"error": "something"}
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _sql

            result = await _sql("SELECT 1")
        assert result == []


# ===================================================================
# _sql_t  — tenant-scoped SQL
# ===================================================================


class TestSqlT:
    """_sql_t injects tenant_id filters into SELECT queries."""

    @pytest.mark.asyncio
    async def test_empty_tenant_passes_through(self) -> None:
        """Empty tenant_id should delegate to _sql without modification."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = [{"id": "1"}]
            from helpers import _sql_t

            result = await _sql_t("SELECT * FROM t", "")

        mock_sql.assert_called_once_with("SELECT * FROM t")
        assert result == [{"id": "1"}]

    @pytest.mark.asyncio
    async def test_invalid_tenant_raises_400(self) -> None:
        """Invalid tenant_id format should raise 400."""
        from helpers import _sql_t

        with pytest.raises(HTTPException) as exc:
            await _sql_t("SELECT * FROM t", "tenant!id")
        assert exc.value.status_code == 400
        assert "Invalid tenant_id format" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_valid_tenant_id_formats(self) -> None:
        """Tenant IDs with underscores and hyphens are valid."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = []
            from helpers import _sql_t

            for valid_id in ("tenant_123", "my-tenant", "a1_b2-c3", "simple"):
                await _sql_t("SELECT * FROM t", valid_id)
        # Just verifying no exception
        assert True

    @pytest.mark.asyncio
    async def test_adds_where_to_bare_query(self) -> None:
        """No WHERE clause: append WHERE tenant_id = ... at end."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = []
            from helpers import _sql_t

            await _sql_t("SELECT * FROM invoice", "t-001")

        mock_sql.assert_called_once_with("SELECT * FROM invoice WHERE tenant_id = 't-001'")

    @pytest.mark.asyncio
    async def test_adds_and_where_to_query_with_where(self) -> None:
        """Existing WHERE clause: append AND tenant_id = ..."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = []
            from helpers import _sql_t

            await _sql_t("SELECT * FROM invoice WHERE status = 'paid'", "t-001")

        mock_sql.assert_called_once_with(
            "SELECT * FROM invoice WHERE status = 'paid' AND tenant_id = 't-001'"
        )

    @pytest.mark.asyncio
    async def test_inserts_before_order_by(self) -> None:
        """Should insert tenant filter before ORDER BY."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = []
            from helpers import _sql_t

            await _sql_t(
                "SELECT * FROM invoice WHERE status = 'paid' ORDER BY created_at DESC",
                "t-001",
            )

        mock_sql.assert_called_once_with(
            "SELECT * FROM invoice WHERE status = 'paid'"
            " AND tenant_id = 't-001' ORDER BY created_at DESC"
        )

    @pytest.mark.asyncio
    async def test_inserts_before_limit(self) -> None:
        """Should insert tenant filter before LIMIT."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = []
            from helpers import _sql_t

            await _sql_t("SELECT * FROM invoice WHERE status = 'paid' LIMIT 10", "t-001")

        mock_sql.assert_called_once_with(
            "SELECT * FROM invoice WHERE status = 'paid' AND tenant_id = 't-001' LIMIT 10"
        )

    @pytest.mark.asyncio
    async def test_inserts_where_before_order_by_no_where(self) -> None:
        """No WHERE clause: insert WHERE ... before ORDER BY."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = []
            from helpers import _sql_t

            await _sql_t("SELECT * FROM invoice ORDER BY created_at DESC", "t-001")

        mock_sql.assert_called_once_with(
            "SELECT * FROM invoice WHERE tenant_id = 't-001' ORDER BY created_at DESC"
        )

    @pytest.mark.asyncio
    async def test_inserts_where_before_limit_no_where(self) -> None:
        """No WHERE clause: insert WHERE ... before LIMIT."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = []
            from helpers import _sql_t

            await _sql_t("SELECT * FROM invoice LIMIT 5", "t-001")

        mock_sql.assert_called_once_with("SELECT * FROM invoice WHERE tenant_id = 't-001' LIMIT 5")

    @pytest.mark.asyncio
    async def test_inserts_before_group_by(self) -> None:
        """Should insert tenant filter before GROUP BY."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = []
            from helpers import _sql_t

            await _sql_t("SELECT status, count(*) FROM invoice GROUP BY status", "t-001")

        mock_sql.assert_called_once_with(
            "SELECT status, count(*) FROM invoice WHERE tenant_id = 't-001' GROUP BY status"
        )

    @pytest.mark.asyncio
    async def test_inserts_before_having(self) -> None:
        """Should insert tenant filter before HAVING."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = []
            from helpers import _sql_t

            await _sql_t(
                "SELECT status, count(*) AS cnt FROM invoice GROUP BY status HAVING cnt > 1",
                "t-001",
            )

        mock_sql.assert_called_once_with(
            "SELECT status, count(*) AS cnt FROM invoice"
            " WHERE tenant_id = 't-001' GROUP BY status HAVING cnt > 1"
        )

    @pytest.mark.asyncio
    async def test_strips_trailing_semicolon(self) -> None:
        """Should strip trailing semicolon before appending WHERE."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = []
            from helpers import _sql_t

            await _sql_t("SELECT * FROM invoice;", "t-001")

        mock_sql.assert_called_once_with("SELECT * FROM invoice WHERE tenant_id = 't-001'")

    @pytest.mark.asyncio
    async def test_multiple_markers_order_by_limit(self) -> None:
        """Should insert before the first marker encountered."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = []
            from helpers import _sql_t

            await _sql_t("SELECT * FROM invoice ORDER BY created_at DESC LIMIT 10", "t-001")

        mock_sql.assert_called_once_with(
            "SELECT * FROM invoice WHERE tenant_id = 't-001' ORDER BY created_at DESC LIMIT 10"
        )

    @pytest.mark.asyncio
    async def test_with_and_where_and_order_by(self) -> None:
        """AND tenant_id should go before ORDER BY."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = []
            from helpers import _sql_t

            await _sql_t(
                "SELECT * FROM invoice WHERE status = 'paid' ORDER BY created_at DESC",
                "t-001",
            )

        mock_sql.assert_called_once_with(
            "SELECT * FROM invoice WHERE status = 'paid'"
            " AND tenant_id = 't-001' ORDER BY created_at DESC"
        )


# ===================================================================
# _paginated
# ===================================================================


class TestPaginated:
    """Paginated tenant-scoped listing."""

    @pytest.mark.asyncio
    async def test_basic_pagination(self) -> None:
        """Should return a slice of rows and total count."""
        mock_rows = [
            {"id": f"r-{i}", "tenant_id": "t-1", "created_at": f"2025-{i:02d}-01"}
            for i in range(1, 11)
        ]

        async def fake_sql(query: str) -> list[dict]:
            if "count(*)" in query:
                return [{"cnt": 10}]
            return mock_rows[::-1]  # reverse to test sorting

        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.side_effect = fake_sql
            from helpers import _paginated

            rows, total = await _paginated(
                tenant_id="t-1",
                table="invoice",
                offset=0,
                limit=3,
                order_by="created_at",
                order_desc=True,
            )

        assert total == 10
        # Should be sorted desc by created_at, so r-10, r-9, r-8
        assert len(rows) == 3
        assert rows[0]["id"] == "r-10"
        assert rows[1]["id"] == "r-9"
        assert rows[2]["id"] == "r-8"

    @pytest.mark.asyncio
    async def test_with_extra_condition(self) -> None:
        """Should include extra WHERE conditions."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.side_effect = lambda q: [{"cnt": 1}] if "count(*)" in q else [{"id": "r-1"}]
            from helpers import _paginated

            rows, total = await _paginated(
                tenant_id="t-1",
                table="invoice",
                where_extra="status = 'paid'",
            )

        assert total == 1
        # Verify both count and fetch queries included the extra condition
        count_call = mock_sql.call_args_list[0][0][0]
        fetch_call = mock_sql.call_args_list[1][0][0]
        assert "status = 'paid'" in count_call
        assert "status = 'paid'" in fetch_call

    @pytest.mark.asyncio
    async def test_strips_sensitive_fields(self) -> None:
        """Should strip sensitive_fields from every row."""
        mock_rows = [
            {"id": "r-1", "tenant_id": "t-1", "password_hash": "secret"},
        ]

        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.side_effect = lambda q: [{"cnt": 1}] if "count(*)" in q else mock_rows
            from helpers import _paginated

            rows, total = await _paginated(
                tenant_id="t-1",
                table="user",
                sensitive_fields={"password_hash"},
            )

        assert total == 1
        assert "password_hash" not in rows[0]
        assert rows[0]["id"] == "r-1"

    @pytest.mark.asyncio
    async def test_empty_tenant_no_where(self) -> None:
        """Empty tenant_id should omit WHERE clause entirely."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.return_value = [{"cnt": 0}]
            from helpers import _paginated

            await _paginated(tenant_id="", table="invoice")

        count_query = mock_sql.call_args_list[0][0][0]
        assert "WHERE" not in count_query


# ===================================================================
# _call  — STDB reducer calls
# ===================================================================


class TestCall:
    """Reducer invocation via STDB call API."""

    @pytest.mark.asyncio
    async def test_successful_call(self) -> None:
        """Should POST to reducer URL and return JSON."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _call

            result = await _call("create_invoice", [{"amount": 100}])

        assert result == {"ok": True}
        call_args = mock_client.post.call_args
        assert "create_invoice" in call_args[0][0]
        assert call_args[1]["json"] == [{"amount": 100}]

    @pytest.mark.asyncio
    async def test_call_with_no_args_defaults_to_empty_list(self) -> None:
        """When args is None, should POST []."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _call

            result = await _call("ping")

        assert result == {"ok": True}
        assert mock_client.post.call_args[1]["json"] == []

    @pytest.mark.asyncio
    async def test_error_response_raises_502(self) -> None:
        """>=400 status should raise HTTPException(502)."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Reducer crashed"
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _call

            with pytest.raises(HTTPException) as exc:
                await _call("bad_reducer")
            assert exc.value.status_code == 502
            assert "Reducer call failed" in exc.value.detail

    @pytest.mark.asyncio
    async def test_json_decode_error_falls_back(self) -> None:
        """If JSON decode fails, return {'ok': True}."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _call

            result = await _call("no_json")
        assert result == {"ok": True}


# ===================================================================
# _sort  — in-memory row sorting
# ===================================================================


class TestSort:
    """Sort rows by key with None handling."""

    def test_sorts_desc_by_default(self) -> None:
        from helpers import _sort

        rows = [{"name": "Bob"}, {"name": "Alice"}, {"name": "Charlie"}]
        sorted_rows = _sort(rows, "name")
        assert [r["name"] for r in sorted_rows] == ["Charlie", "Bob", "Alice"]

    def test_sorts_ascending(self) -> None:
        from helpers import _sort

        rows = [{"name": "Bob"}, {"name": "Alice"}, {"name": "Charlie"}]
        sorted_rows = _sort(rows, "name", desc=False)
        assert [r["name"] for r in sorted_rows] == ["Alice", "Bob", "Charlie"]

    def test_none_values_sorted_last_desc(self) -> None:
        """None values should sort to the end in desc order."""
        from helpers import _sort

        rows = [{"name": "Bob"}, {"name": None}, {"name": "Alice"}]
        sorted_rows = _sort(rows, "name", desc=True)
        assert sorted_rows[-1]["name"] is None
        assert sorted_rows[0]["name"] == "Bob"

    def test_none_values_sorted_last_asc(self) -> None:
        """None values should sort to the end in asc order."""
        from helpers import _sort

        rows = [{"name": "Bob"}, {"name": None}, {"name": "Alice"}]
        sorted_rows = _sort(rows, "name", desc=False)
        assert sorted_rows[-1]["name"] is None
        assert sorted_rows[0]["name"] == "Alice"

    def test_missing_key_treated_as_none(self) -> None:
        from helpers import _sort

        rows = [{"name": "Bob"}, {"notname": "X"}, {"name": "Alice"}]
        sorted_rows = _sort(rows, "name", desc=True)
        assert len(sorted_rows) == 3
        # The row without 'name' should be treated as None
        assert "notname" in sorted_rows[-1]

    def test_empty_list(self) -> None:
        from helpers import _sort

        assert _sort([], "name") == []

    def test_same_values_stable(self) -> None:
        from helpers import _sort

        rows = [{"name": "Alice", "id": 1}, {"name": "Alice", "id": 2}]
        sorted_rows = _sort(rows, "name")
        # Original order should be preserved for equal keys
        assert sorted_rows[0]["id"] == 1
        assert sorted_rows[1]["id"] == 2
