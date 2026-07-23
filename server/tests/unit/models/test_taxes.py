"""TaxRate models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestTaxRateCreate:
    def test_valid(self) -> None:
        from models import TaxRateCreate

        m = TaxRateCreate(name="Sales Tax", rate=8.5)
        assert m.name == "Sales Tax"
        assert m.rate == 8.5
        assert m.is_default is False

    def test_rate_negative(self) -> None:
        from models import TaxRateCreate

        with pytest.raises(ValidationError):
            TaxRateCreate(name="Bad", rate=-1)

    def test_rate_too_high(self) -> None:
        from models import TaxRateCreate

        with pytest.raises(ValidationError):
            TaxRateCreate(name="Bad", rate=100.01)
