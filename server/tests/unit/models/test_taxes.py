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

    def test_name_empty(self) -> None:
        from models import TaxRateCreate

        with pytest.raises(ValidationError):
            TaxRateCreate(name="", rate=5.0)

    def test_name_too_long(self) -> None:
        from models import TaxRateCreate

        with pytest.raises(ValidationError):
            TaxRateCreate(name="x" * 101, rate=5.0)

    def test_rate_zero(self) -> None:
        from models import TaxRateCreate

        m = TaxRateCreate(name="Zero", rate=0)
        assert m.rate == 0
        assert m.is_default is False

    def test_rate_max_boundary(self) -> None:
        from models import TaxRateCreate

        m = TaxRateCreate(name="Max", rate=100)
        assert m.rate == 100

    def test_is_default_true(self) -> None:
        from models import TaxRateCreate

        m = TaxRateCreate(name="Default", rate=8.5, is_default=True)
        assert m.is_default is True


class TestTaxRateUpdate:
    def test_valid(self) -> None:
        from models import TaxRateUpdate

        m = TaxRateUpdate(name="Updated Tax", rate=9.25, is_default=True)
        assert m.name == "Updated Tax"
        assert m.rate == 9.25
        assert m.is_default is True

    def test_rate_negative(self) -> None:
        from models import TaxRateUpdate

        with pytest.raises(ValidationError):
            TaxRateUpdate(name="Bad", rate=-1)

    def test_rate_too_high(self) -> None:
        from models import TaxRateUpdate

        with pytest.raises(ValidationError):
            TaxRateUpdate(name="Bad", rate=100.01)

    def test_name_empty(self) -> None:
        from models import TaxRateUpdate

        with pytest.raises(ValidationError):
            TaxRateUpdate(name="", rate=5.0)

    def test_name_too_long(self) -> None:
        from models import TaxRateUpdate

        with pytest.raises(ValidationError):
            TaxRateUpdate(name="x" * 101, rate=5.0)

    def test_defaults(self) -> None:
        from models import TaxRateUpdate

        m = TaxRateUpdate(name="Tax", rate=7.5)
        assert m.is_default is False
