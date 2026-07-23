"""Invoice models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestInvoiceCreate:
    def test_valid(self) -> None:
        from models import InvoiceCreate

        m = InvoiceCreate(customer_id="c-001")
        assert m.customer_id == "c-001"
        assert m.currency == "USD"
        assert m.due_date == 0
        assert m.discount_amount == 0
        assert m.discount_percent == 0

    def test_missing_customer_id_raises(self) -> None:
        from models import InvoiceCreate

        with pytest.raises(ValidationError):
            InvoiceCreate()

    def test_discount_percent_out_of_range_high(self) -> None:
        from models import InvoiceCreate

        with pytest.raises(ValidationError):
            InvoiceCreate(customer_id="c-001", discount_percent=101)

    def test_discount_percent_out_of_range_low(self) -> None:
        from models import InvoiceCreate

        with pytest.raises(ValidationError):
            InvoiceCreate(customer_id="c-001", discount_percent=-1)

    def test_discount_amount_negative(self) -> None:
        from models import InvoiceCreate

        with pytest.raises(ValidationError):
            InvoiceCreate(customer_id="c-001", discount_amount=-0.01)

    def test_due_date_negative(self) -> None:
        from models import InvoiceCreate

        with pytest.raises(ValidationError):
            InvoiceCreate(customer_id="c-001", due_date=-1)

    def test_notes_max_length(self) -> None:
        from models import InvoiceCreate

        with pytest.raises(ValidationError):
            InvoiceCreate(customer_id="c-001", notes="x" * 2001)

    def test_currency_max_length(self) -> None:
        from models import InvoiceCreate

        with pytest.raises(ValidationError):
            InvoiceCreate(customer_id="c-001", currency="ABCD")


class TestInvoiceStatusUpdate:
    def test_valid(self) -> None:
        from models import InvoiceStatusUpdate

        m = InvoiceStatusUpdate(status="paid")
        assert m.status == "paid"

    def test_empty_status_raises(self) -> None:
        from models import InvoiceStatusUpdate

        with pytest.raises(ValidationError):
            InvoiceStatusUpdate(status="")


class TestInvoiceLineItemCreate:
    def test_valid(self) -> None:
        from models import InvoiceLineItemCreate

        m = InvoiceLineItemCreate(
            description="Labor charge",
            quantity=2,
            unit_price=75.00,
        )
        assert m.description == "Labor charge"
        assert m.quantity == 2
        assert m.unit_price == 75.00
        assert m.item_type == "service"  # default

    def test_quantity_negative(self) -> None:
        from models import InvoiceLineItemCreate

        with pytest.raises(ValidationError):
            InvoiceLineItemCreate(quantity=-1)

    def test_unit_price_negative(self) -> None:
        from models import InvoiceLineItemCreate

        with pytest.raises(ValidationError):
            InvoiceLineItemCreate(unit_price=-0.01)

    def test_description_max_length(self) -> None:
        from models import InvoiceLineItemCreate

        with pytest.raises(ValidationError):
            InvoiceLineItemCreate(description="x" * 501)


class TestBulkInvoiceStatusUpdate:
    def test_valid(self) -> None:
        from models import BulkInvoiceStatusUpdate

        m = BulkInvoiceStatusUpdate(
            invoice_ids=["inv-001", "inv-002"],
            status="paid",
        )
        assert m.invoice_ids == ["inv-001", "inv-002"]
        assert m.status == "paid"

    def test_empty_invoice_ids_raises(self) -> None:
        from models import BulkInvoiceStatusUpdate

        with pytest.raises(ValidationError):
            BulkInvoiceStatusUpdate(invoice_ids=[], status="paid")

    def test_too_many_invoice_ids_raises(self) -> None:
        from models import BulkInvoiceStatusUpdate

        with pytest.raises(ValidationError):
            BulkInvoiceStatusUpdate(
                invoice_ids=[str(i) for i in range(501)],
                status="paid",
            )

    def test_missing_status_raises(self) -> None:
        from models import BulkInvoiceStatusUpdate

        with pytest.raises(ValidationError):
            BulkInvoiceStatusUpdate(invoice_ids=["inv-001"])
