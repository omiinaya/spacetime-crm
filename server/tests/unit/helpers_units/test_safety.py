"""Unit tests for helpers._safe_customer and _safe_id."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException


# ===================================================================
# _safe_customer
# ===================================================================


class TestSafeCustomer:
    """Strip CUSTOMER_SENSITIVE_FIELDS from customer dicts."""

    def test_strips_sensitive_fields(self) -> None:
        from helpers import _safe_customer

        raw = {
            "id": "c-001",
            "name": "Alice",
            "email": "alice@example.com",
            "portal_password_hash": "abc123hash",
        }
        safe = _safe_customer(raw)
        assert "portal_password_hash" not in safe
        assert safe["id"] == "c-001"
        assert safe["name"] == "Alice"
        assert safe["email"] == "alice@example.com"

    def test_passes_through_non_sensitive(self) -> None:
        from helpers import _safe_customer

        raw = {"id": "c-002", "company": "Acme Inc", "phone": "555-0100"}
        safe = _safe_customer(raw)
        assert safe == raw

    def test_handles_empty_dict(self) -> None:
        from helpers import _safe_customer

        assert _safe_customer({}) == {}

    def test_keeps_extra_fields(self) -> None:
        from helpers import _safe_customer

        raw = {"id": "c-003", "portal_password_hash": "secret", "notes": "VIP"}
        safe = _safe_customer(raw)
        assert "portal_password_hash" not in safe
        assert safe["notes"] == "VIP"


# ===================================================================
# _safe_id
# ===================================================================


class TestSafeId:
    """ID format validation."""

    def test_valid_ids(self) -> None:
        from helpers import _safe_id

        for valid in (
            "abc123",
            "user_001",
            "my-tenant-id",
            "a1_b2-c3",
            "single",
            "12345",
            "tenant_001-abc",
        ):
            assert _safe_id(valid) == valid

    def test_empty_string_raises(self) -> None:
        from helpers import _safe_id

        with pytest.raises(HTTPException) as exc:
            _safe_id("")
        assert exc.value.status_code == 400

    def test_special_chars_raises(self) -> None:
        from helpers import _safe_id

        for bad in ("abc!@#", "hello world", "id;drop", "path/../", "SELECT*", "';--"):
            with pytest.raises(HTTPException) as exc:
                _safe_id(bad)
            assert exc.value.status_code == 400

    def test_whitespace_raises(self) -> None:
        from helpers import _safe_id

        with pytest.raises(HTTPException):
            _safe_id("has space")

    def test_none_raises_type_error(self) -> None:
        """None should fail because .replace can't be called on None."""
        from helpers import _safe_id

        with pytest.raises(Exception):
            _safe_id(None)  # type: ignore[arg-type]
