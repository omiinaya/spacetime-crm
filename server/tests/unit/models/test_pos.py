"""POS models and SetPin / PosLogin — regex patterns."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestPOSCreate:
    def test_valid(self) -> None:
        from models import POSCreate

        m = POSCreate()
        assert m.customer_name == "Walk-in"
        assert m.payment_method == "cash"

    def test_invalid_payment_method(self) -> None:
        from models import POSCreate

        with pytest.raises(ValidationError, match="payment_method"):
            POSCreate(payment_method="check")

    def test_valid_payment_methods(self) -> None:
        from models import POSCreate

        for method in ("cash", "card", "invoice"):
            m = POSCreate(payment_method=method)
            assert m.payment_method == method

    def test_discount_amount_negative(self) -> None:
        from models import POSCreate

        with pytest.raises(ValidationError):
            POSCreate(discount_amount=-1)


class TestPOSAddItem:
    def test_valid(self) -> None:
        from models import POSAddItem

        m = POSAddItem(
            sale_id="sale-001",
            product_id="prod-001",
            product_name="USB Cable",
            quantity=2,
            unit_price=9.99,
        )
        assert m.quantity == 2

    def test_quantity_zero_raises(self) -> None:
        """POSAddItem.quantity has gt=0."""
        from models import POSAddItem

        with pytest.raises(ValidationError):
            POSAddItem(
                sale_id="sale-001",
                product_id="prod-001",
                product_name="Cable",
                quantity=0,
                unit_price=5,
            )

    def test_unit_price_negative_raises(self) -> None:
        from models import POSAddItem

        with pytest.raises(ValidationError):
            POSAddItem(
                sale_id="sale-001",
                product_id="prod-001",
                product_name="Cable",
                quantity=1,
                unit_price=-5,
            )


class TestSetPinRequest:
    def test_valid_pin(self) -> None:
        from models import SetPinRequest

        m = SetPinRequest(pin="1234")
        assert m.pin == "1234"

    def test_empty_pin_default(self) -> None:
        from models import SetPinRequest

        m = SetPinRequest()
        assert m.pin == ""

    def test_pin_with_letters_raises(self) -> None:
        """Pattern is ^\\d{0,10}$."""
        from models import SetPinRequest

        with pytest.raises(ValidationError):
            SetPinRequest(pin="abcd")

    def test_pin_too_long(self) -> None:
        from models import SetPinRequest

        with pytest.raises(ValidationError):
            SetPinRequest(pin="12345678901")


class TestPosLoginRequest:
    def test_valid(self) -> None:
        from models import PosLoginRequest

        m = PosLoginRequest(user_id="u-001", pin="1234")
        assert m.pin == "1234"

    def test_pin_too_short(self) -> None:
        """min_length=4 for PosLoginRequest."""
        from models import PosLoginRequest

        with pytest.raises(ValidationError):
            PosLoginRequest(user_id="u-001", pin="123")

    def test_pin_too_long(self) -> None:
        from models import PosLoginRequest

        with pytest.raises(ValidationError):
            PosLoginRequest(user_id="u-001", pin="12345678901")

    def test_pin_with_letters_raises(self) -> None:
        from models import PosLoginRequest

        with pytest.raises(ValidationError):
            PosLoginRequest(user_id="u-001", pin="12a4")
