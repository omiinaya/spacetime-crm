"""SavePaymentMethod — last4 pattern, exp_month/exp_year ranges."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestSavePaymentMethodRequest:
    def test_valid(self) -> None:
        from models import SavePaymentMethodRequest

        m = SavePaymentMethodRequest(
            customer_id="c-001",
            stripe_payment_method_id="pm_1234567890",
            brand="Visa",
            last4="4242",
            exp_month=12,
            exp_year=2028,
        )
        assert m.last4 == "4242"
        assert m.exp_month == 12
        assert m.exp_year == 2028

    def test_invalid_last4_pattern(self) -> None:
        """last4 must match ^\\d{4}$."""
        from models import SavePaymentMethodRequest

        with pytest.raises(ValidationError, match="last4"):
            SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="abc",
                exp_month=12,
                exp_year=2028,
            )

    def test_last4_too_short(self) -> None:
        from models import SavePaymentMethodRequest

        with pytest.raises(ValidationError):
            SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="123",
                exp_month=12,
                exp_year=2028,
            )

    def test_last4_too_long(self) -> None:
        from models import SavePaymentMethodRequest

        with pytest.raises(ValidationError):
            SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="12345",
                exp_month=12,
                exp_year=2028,
            )

    def test_exp_month_too_low(self) -> None:
        from models import SavePaymentMethodRequest

        with pytest.raises(ValidationError):
            SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="4242",
                exp_month=0,
                exp_year=2028,
            )

    def test_exp_month_too_high(self) -> None:
        from models import SavePaymentMethodRequest

        with pytest.raises(ValidationError):
            SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="4242",
                exp_month=13,
                exp_year=2028,
            )

    def test_exp_year_too_low(self) -> None:
        from models import SavePaymentMethodRequest

        with pytest.raises(ValidationError):
            SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="4242",
                exp_month=12,
                exp_year=2019,
            )

    def test_exp_year_too_high(self) -> None:
        from models import SavePaymentMethodRequest

        with pytest.raises(ValidationError):
            SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="4242",
                exp_month=12,
                exp_year=2101,
            )

    def test_brand_max_length(self) -> None:
        from models import SavePaymentMethodRequest

        with pytest.raises(ValidationError):
            SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="x" * 51,
                last4="4242",
                exp_month=12,
                exp_year=2028,
            )
