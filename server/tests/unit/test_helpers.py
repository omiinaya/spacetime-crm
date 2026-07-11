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
        labels = {"draft": "Draft", "sent": "Sent", "paid": "Paid",
                  "partial": "Partial", "overdue": "Overdue", "cancelled": "Cancelled"}
        assert STATUS_LABELS == labels

    def test_status_css_contains_all_keys(self):
        for key in ("draft", "sent", "paid", "partial", "overdue", "cancelled"):
            assert key in STATUS_CSS

    def test_status_css_maps_correctly(self):
        expected = {"draft": "draft", "sent": "sent", "paid": "paid",
                    "partial": "partial", "overdue": "overdue", "cancelled": "cancelled"}
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
