"""Purchase Order models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestPurchaseOrderCreate:
    def test_valid(self) -> None:
        from models import PurchaseOrderCreate

        m = PurchaseOrderCreate(vendor_name="Acme Supplies")
        assert m.vendor_name == "Acme Supplies"
        assert m.currency == "USD"
        assert m.shipping_cost == 0

    def test_empty_vendor_raises(self) -> None:
        from models import PurchaseOrderCreate

        with pytest.raises(ValidationError):
            PurchaseOrderCreate(vendor_name="")

    def test_shipping_cost_negative(self) -> None:
        from models import PurchaseOrderCreate

        with pytest.raises(ValidationError):
            PurchaseOrderCreate(vendor_name="Acme", shipping_cost=-1)


class TestPOLineItemCreate:
    def test_valid(self) -> None:
        from models import POLineItemCreate

        m = POLineItemCreate()
        assert m.quantity == 1
        assert m.unit_price == 0
        assert m.product_id == ""

    def test_quantity_negative(self) -> None:
        from models import POLineItemCreate

        with pytest.raises(ValidationError):
            POLineItemCreate(quantity=-1)

    def test_unit_price_negative(self) -> None:
        from models import POLineItemCreate

        with pytest.raises(ValidationError):
            POLineItemCreate(unit_price=-0.01)


class TestPOReceiveItem:
    def test_valid(self) -> None:
        from models import POReceiveItem

        m = POReceiveItem(received_quantity=10)
        assert m.received_quantity == 10
        assert m.items == []

    def test_received_quantity_negative(self) -> None:
        from models import POReceiveItem

        with pytest.raises(ValidationError):
            POReceiveItem(received_quantity=-1)


class TestPOApprovalAction:
    def test_valid(self) -> None:
        from models import POApprovalAction

        m = POApprovalAction(user_id="u-001")
        assert m.user_id == "u-001"

    def test_empty_user_id_raises(self) -> None:
        from models import POApprovalAction

        with pytest.raises(ValidationError):
            POApprovalAction(user_id="")
