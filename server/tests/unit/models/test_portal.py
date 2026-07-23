"""Portal — minimal coverage."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestPortalLoginRequest:
    def test_valid(self) -> None:
        from models import PortalLoginRequest

        m = PortalLoginRequest(email="user@portal.com", password="abc123")
        assert m.email == "user@portal.com"


class TestPortalNoteCreate:
    def test_valid(self) -> None:
        from models import PortalNoteCreate

        m = PortalNoteCreate(content="Customer note")
        assert m.content == "Customer note"

    def test_content_too_long(self) -> None:
        from models import PortalNoteCreate

        with pytest.raises(ValidationError):
            PortalNoteCreate(content="x" * 5001)


class TestPortalPaymentCreate:
    def test_valid(self) -> None:
        from models import PortalPaymentCreate

        m = PortalPaymentCreate(invoice_id="inv-001", amount=99.99)
        assert m.method == "card"

    def test_amount_zero_raises(self) -> None:
        from models import PortalPaymentCreate

        with pytest.raises(ValidationError):
            PortalPaymentCreate(invoice_id="inv-001", amount=0)
