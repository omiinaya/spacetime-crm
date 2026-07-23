"""Customer models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestCustomerCreate:
    def test_valid(self) -> None:
        from models import CustomerCreate

        m = CustomerCreate(first_name="Alice", last_name="Smith")
        assert m.first_name == "Alice"
        assert m.last_name == "Smith"

    def test_defaults_applied(self) -> None:
        from models import CustomerCreate

        m = CustomerCreate(first_name="Bob", last_name="Jones")
        # All optional fields should have empty string defaults
        assert m.email == ""
        assert m.phone == ""
        assert m.mobile == ""
        assert m.company == ""
        assert m.address_line1 == ""
        assert m.address_line2 == ""
        assert m.city == ""
        assert m.state == ""
        assert m.zip == ""
        assert m.notes == ""
        assert m.tags == ""

    def test_first_name_too_short(self) -> None:
        from models import CustomerCreate

        with pytest.raises(ValidationError, match="first_name"):
            CustomerCreate(first_name="", last_name="Smith")

    def test_first_name_too_long(self) -> None:
        from models import CustomerCreate

        with pytest.raises(ValidationError):
            CustomerCreate(first_name="x" * 101, last_name="Smith")

    def test_last_name_too_long(self) -> None:
        from models import CustomerCreate

        with pytest.raises(ValidationError):
            CustomerCreate(first_name="Alice", last_name="x" * 101)

    def test_email_max_length(self) -> None:
        from models import CustomerCreate

        with pytest.raises(ValidationError):
            CustomerCreate(
                first_name="Alice",
                last_name="Smith",
                email="x" * 256,
            )

    def test_notes_max_length(self) -> None:
        from models import CustomerCreate

        with pytest.raises(ValidationError):
            CustomerCreate(
                first_name="Alice",
                last_name="Smith",
                notes="x" * 2001,
            )

    def test_tags_max_length(self) -> None:
        from models import CustomerCreate

        with pytest.raises(ValidationError):
            CustomerCreate(
                first_name="Alice",
                last_name="Smith",
                tags="x" * 501,
            )

    def test_missing_first_name_raises(self) -> None:
        from models import CustomerCreate

        with pytest.raises(ValidationError):
            CustomerCreate(last_name="Smith")

    def test_missing_last_name_raises(self) -> None:
        from models import CustomerCreate

        with pytest.raises(ValidationError):
            CustomerCreate(first_name="Alice")
