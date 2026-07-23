"""Estimate models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestEstimateCreate:
    def test_valid(self) -> None:
        from models import EstimateCreate

        m = EstimateCreate(customer_id="c-001")
        assert m.customer_id == "c-001"
        assert m.currency == "USD"
        assert m.tax_rate == 0

    def test_tax_rate_negative(self) -> None:
        from models import EstimateCreate

        with pytest.raises(ValidationError):
            EstimateCreate(customer_id="c-001", tax_rate=-1)

    def test_tax_rate_too_high(self) -> None:
        from models import EstimateCreate

        with pytest.raises(ValidationError):
            EstimateCreate(customer_id="c-001", tax_rate=101)

    def test_discount_amount_negative(self) -> None:
        from models import EstimateCreate

        with pytest.raises(ValidationError):
            EstimateCreate(customer_id="c-001", discount_amount=-0.01)
