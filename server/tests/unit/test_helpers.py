"""Unit tests for server/helpers.py — module-level constants, structure, and edge cases.

The helpers_units/ subdirectory contains detailed function-level tests for
_sql, _sql_t, _paginated, _call, _sort, _log_audit, _get_webhook_subscriptions,
_fire_webhook, require_role, _safe_id, get_current_user, and _safe_customer.

This file covers:
  - Module-level constants (STATUS_LABELS, STATUS_CSS, CUSTOMER_SENSITIVE_FIELDS,
    TEMPLATE_DIR, jinja_env, security, logger)
  - Module structure (docstring, importability)
  - Edge cases not covered in helpers_units/
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBearer
from jinja2 import Environment

# ===================================================================
# Module-level constants
# ===================================================================


class TestStatusLabels:
    """STATUS_LABELS maps internal status keys to human-readable labels."""

    def test_status_labels_content(self) -> None:
        from helpers import STATUS_LABELS

        assert STATUS_LABELS == {
            "draft": "Draft",
            "sent": "Sent",
            "paid": "Paid",
            "partial": "Partial",
            "overdue": "Overdue",
            "cancelled": "Cancelled",
        }

    def test_status_labels_keys_match_css_keys(self) -> None:
        """STATUS_LABELS and STATUS_CSS should have the same set of keys."""
        from helpers import STATUS_CSS, STATUS_LABELS

        assert set(STATUS_LABELS.keys()) == set(STATUS_CSS.keys())

    def test_status_labels_values_are_title_case(self) -> None:
        from helpers import STATUS_LABELS

        for key, label in STATUS_LABELS.items():
            assert label[0].isupper(), f"Label for '{key}' should start with uppercase"

    def test_status_labels_count(self) -> None:
        from helpers import STATUS_LABELS

        assert len(STATUS_LABELS) == 6


class TestStatusCss:
    """STATUS_CSS maps internal status keys to CSS class names."""

    def test_status_css_content(self) -> None:
        from helpers import STATUS_CSS

        assert STATUS_CSS == {
            "draft": "draft",
            "sent": "sent",
            "paid": "paid",
            "partial": "partial",
            "overdue": "overdue",
            "cancelled": "cancelled",
        }

    def test_status_css_values_match_keys(self) -> None:
        """Each CSS class should match its status key."""
        from helpers import STATUS_CSS

        for key, css_class in STATUS_CSS.items():
            assert css_class == key


class TestCustomerSensitiveFields:
    """CUSTOMER_SENSITIVE_FIELDS defines fields stripped from customer dicts."""

    def test_contains_portal_password_hash(self) -> None:
        from helpers import CUSTOMER_SENSITIVE_FIELDS

        assert "portal_password_hash" in CUSTOMER_SENSITIVE_FIELDS

    def test_is_a_set(self) -> None:
        from helpers import CUSTOMER_SENSITIVE_FIELDS

        assert isinstance(CUSTOMER_SENSITIVE_FIELDS, set)

    def test_non_empty(self) -> None:
        from helpers import CUSTOMER_SENSITIVE_FIELDS

        assert len(CUSTOMER_SENSITIVE_FIELDS) > 0


class TestTemplateDir:
    """TEMPLATE_DIR points to the Jinja2 template directory."""

    def test_is_path(self) -> None:
        from helpers import TEMPLATE_DIR

        assert isinstance(TEMPLATE_DIR, Path)

    def test_name_is_templates(self) -> None:
        from helpers import TEMPLATE_DIR

        assert TEMPLATE_DIR.name == "templates"

    def test_exists(self) -> None:
        from helpers import TEMPLATE_DIR

        assert TEMPLATE_DIR.exists()

    def test_is_directory(self) -> None:
        from helpers import TEMPLATE_DIR

        assert TEMPLATE_DIR.is_dir()


class TestJinjaEnv:
    """jinja_env is the shared Jinja2 Environment."""

    def test_is_environment(self) -> None:
        from helpers import jinja_env

        assert isinstance(jinja_env, Environment)

    def test_loader_is_file_system_loader(self) -> None:
        from helpers import jinja_env
        from jinja2 import FileSystemLoader

        assert isinstance(jinja_env.loader, FileSystemLoader)


class TestSecurity:
    """security is the HTTPBearer instance for JWT auth."""

    def test_is_http_bearer(self) -> None:
        from helpers import security

        assert isinstance(security, HTTPBearer)

    def test_auto_error_false(self) -> None:
        """auto_error=False means missing credentials return None, not 401."""
        from helpers import security

        assert security.auto_error is False


class TestLogger:
    """logger is the module-level logger."""

    def test_is_logger(self) -> None:
        from helpers import logger

        assert isinstance(logger, logging.Logger)

    def test_name_is_helpers(self) -> None:
        from helpers import logger

        assert logger.name == "helpers"


# ===================================================================
# Module structure
# ===================================================================


class TestModuleStructure:
    """Verify the helpers module is importable and well-formed."""

    def test_module_docstring(self) -> None:
        import helpers

        assert helpers.__doc__ is not None
        assert "STDB helpers" in helpers.__doc__

    def test_module_has_all_expected_names(self) -> None:
        """All expected public and private names should be importable."""
        from helpers import (
            _call,
            _fire_webhook,
            _get_webhook_subscriptions,
            _log_audit,
            _paginated,
            _safe_customer,
            _safe_id,
            _sort,
            _sql,
            _sql_t,
            get_current_user,
            require_role,
        )

        # If we got here, all imports succeeded
        assert callable(_sql)
        assert callable(_sql_t)
        assert callable(_paginated)
        assert callable(_call)
        assert callable(_sort)
        assert callable(_log_audit)
        assert callable(_get_webhook_subscriptions)
        assert callable(_fire_webhook)
        assert callable(require_role)
        assert callable(_safe_id)
        assert callable(get_current_user)
        assert callable(_safe_customer)


# ===================================================================
# Edge cases not covered in helpers_units/
# ===================================================================


class TestSqlEdgeCases:
    """Edge cases for _sql not covered in helpers_units/test_sql.py."""

    @pytest.mark.asyncio
    async def test_multiple_table_results_merged(self) -> None:
        """Should merge rows from multiple table results in the response."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                "rows": [["u-1", "Alice"]],
                "schema": {
                    "elements": [
                        {"name": {"some": "id"}},
                        {"name": {"some": "name"}},
                    ]
                },
            },
            {
                "rows": [["u-2", "Bob"]],
                "schema": {
                    "elements": [
                        {"name": {"some": "id"}},
                        {"name": {"some": "name"}},
                    ]
                },
            },
        ]
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _sql

            result = await _sql("SELECT id, name FROM user")

        assert len(result) == 2
        assert result[0] == {"id": "u-1", "name": "Alice"}
        assert result[1] == {"id": "u-2", "name": "Bob"}

    @pytest.mark.asyncio
    async def test_logs_error_on_failure(self) -> None:
        """Should log the error before raising HTTPException(502)."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal server error"
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("helpers.get_http_client", return_value=mock_client):
            with patch("helpers.logger") as mock_logger:
                from helpers import _sql

                with pytest.raises(HTTPException) as exc:
                    await _sql("SELECT * FROM bad_table")

                assert exc.value.status_code == 502
                mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_schema_without_elements_key(self) -> None:
        """Should handle schema dict that has no 'elements' key."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"rows": [["v1"]], "schema": {}}]
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _sql

            result = await _sql("SELECT count(*) FROM t")

        assert result == [{}]


class TestPaginatedEdgeCases:
    """Edge cases for _paginated not covered in helpers_units/test_sql.py."""

    @pytest.mark.asyncio
    async def test_max_fetch_zero_fetches_all(self) -> None:
        """When max_fetch=0 (falsy), should fetch all rows."""
        mock_rows = [{"id": f"r-{i}", "created_at": f"2025-01-0{i}"} for i in range(1, 6)]

        async def fake_sql(query: str) -> list[dict]:
            if "count(*)" in query:
                return [{"cnt": 5}]
            return mock_rows

        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.side_effect = fake_sql
            from helpers import _paginated

            rows, total = await _paginated(tenant_id="t-1", table="invoice", max_fetch=0, limit=10)

        assert total == 5
        assert len(rows) == 5

    @pytest.mark.asyncio
    async def test_max_fetch_limits_fetch(self) -> None:
        """When max_fetch < total, should only fetch max_fetch rows."""
        mock_rows = [{"id": f"r-{i}", "created_at": f"2025-01-0{i}"} for i in range(1, 11)]

        async def fake_sql(query: str) -> list[dict]:
            if "count(*)" in query:
                return [{"cnt": 10}]
            # Simulate STDB returning only max_fetch rows
            return mock_rows[:3]

        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.side_effect = fake_sql
            from helpers import _paginated

            rows, total = await _paginated(tenant_id="t-1", table="invoice", max_fetch=3, limit=10)

        assert total == 10
        assert len(rows) == 3

    @pytest.mark.asyncio
    async def test_empty_result_set(self) -> None:
        """Should handle zero rows gracefully."""
        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.side_effect = lambda q: [{"cnt": 0}] if "count(*)" in q else []
            from helpers import _paginated

            rows, total = await _paginated(tenant_id="t-1", table="invoice")

        assert total == 0
        assert rows == []

    @pytest.mark.asyncio
    async def test_ascending_order(self) -> None:
        """Should sort ascending when order_desc=False."""
        mock_rows = [{"id": f"r-{i}", "created_at": f"2025-01-0{i}"} for i in range(1, 6)]

        async def fake_sql(query: str) -> list[dict]:
            if "count(*)" in query:
                return [{"cnt": 5}]
            return mock_rows[::-1]  # reversed to test sorting

        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.side_effect = fake_sql
            from helpers import _paginated

            rows, total = await _paginated(
                tenant_id="t-1", table="invoice", order_desc=False, limit=10
            )

        assert total == 5
        # Ascending: r-1, r-2, r-3, r-4, r-5
        assert rows[0]["id"] == "r-1"
        assert rows[-1]["id"] == "r-5"

    @pytest.mark.asyncio
    async def test_offset_beyond_total(self) -> None:
        """Offset beyond total should return empty list."""
        mock_rows = [{"id": f"r-{i}", "created_at": f"2025-01-0{i}"} for i in range(1, 4)]

        async def fake_sql(query: str) -> list[dict]:
            if "count(*)" in query:
                return [{"cnt": 3}]
            return mock_rows

        with patch("helpers._sql", new_callable=AsyncMock) as mock_sql:
            mock_sql.side_effect = fake_sql
            from helpers import _paginated

            rows, total = await _paginated(tenant_id="t-1", table="invoice", offset=10, limit=5)

        assert total == 3
        assert rows == []


class TestCallEdgeCases:
    """Edge cases for _call not covered in helpers_units/test_sql.py."""

    @pytest.mark.asyncio
    async def test_call_with_empty_list_args(self) -> None:
        """Should POST empty list when args is []."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _call

            result = await _call("reducer", [])

        assert result == {"ok": True}
        assert mock_client.post.call_args[1]["json"] == []

    @pytest.mark.asyncio
    async def test_call_logs_error_on_failure(self) -> None:
        """Should log the error when reducer call fails."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal error"
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("helpers.get_http_client", return_value=mock_client):
            with patch("helpers.logger") as mock_logger:
                from helpers import _call

                with pytest.raises(HTTPException) as exc:
                    await _call("bad_reducer")

                assert exc.value.status_code == 502
                mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_url_uses_settings(self) -> None:
        """Should construct URL from settings.stdb_call_url."""
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("helpers.get_http_client", return_value=mock_client):
            from helpers import _call, settings

            await _call("my_reducer", [1, 2])

        call_url = mock_client.post.call_args[0][0]
        assert settings.stdb_call_url in call_url
        assert "my_reducer" in call_url
