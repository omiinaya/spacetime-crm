"""Payment model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestPaymentCreate:
    def test_valid(self) -> None:
        from models import PaymentCreate

        m = PaymentCreate(
            invoice_id="inv-001",
            customer_id="c-001",
            amount=150.00,
        )
        assert m.invoice_id == "inv-001"
        assert m.customer_id == "c-001"
        assert m.amount == 150.00
        assert m.method == "cash"
        assert m.currency == "USD"

    def test_amount_zero_raises(self) -> None:
        """PaymentCreate amount has gt=0 (strictly greater than zero)."""
        from models import PaymentCreate

        with pytest.raises(ValidationError):
            PaymentCreate(
                invoice_id="inv-001",
                customer_id="c-001",
                amount=0,
            )

    def test_amount_negative_raises(self) -> None:
        from models import PaymentCreate

        with pytest.raises(ValidationError):
            PaymentCreate(
                invoice_id="inv-001",
                customer_id="c-001",
                amount=-50,
            )

    def test_missing_invoice_id_raises(self) -> None:
        from models import PaymentCreate

        with pytest.raises(ValidationError):
            PaymentCreate(customer_id="c-001", amount=100)

    def test_missing_customer_id_raises(self) -> None:
        from models import PaymentCreate

        with pytest.raises(ValidationError):
            PaymentCreate(invoice_id="inv-001", amount=100)

    def test_missing_amount_raises(self) -> None:
        from models import PaymentCreate

        with pytest.raises(ValidationError):
            PaymentCreate(invoice_id="inv-001", customer_id="c-001")

    def test_reference_max_length(self) -> None:
        from models import PaymentCreate

        with pytest.raises(ValidationError):
            PaymentCreate(
                invoice_id="inv-001",
                customer_id="c-001",
                amount=100,
                reference="x" * 256,
            )
