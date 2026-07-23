"""StockTransfer / Inventory — gt / ge constraints and Product models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestStockTransferRequest:
    def test_valid(self) -> None:
        from models import StockTransferRequest

        m = StockTransferRequest(
            source_product_id="prod-001",
            destination_product_id="prod-002",
            quantity=10,
        )
        assert m.quantity == 10

    def test_quantity_zero_raises(self) -> None:
        """StockTransferRequest.quantity has gt=0 (strictly > 0)."""
        from models import StockTransferRequest

        with pytest.raises(ValidationError):
            StockTransferRequest(
                source_product_id="prod-001",
                destination_product_id="prod-002",
                quantity=0,
            )

    def test_quantity_negative_raises(self) -> None:
        from models import StockTransferRequest

        with pytest.raises(ValidationError):
            StockTransferRequest(
                source_product_id="prod-001",
                destination_product_id="prod-002",
                quantity=-5,
            )

    def test_empty_source_id_raises(self) -> None:
        from models import StockTransferRequest

        with pytest.raises(ValidationError):
            StockTransferRequest(
                source_product_id="",
                destination_product_id="prod-002",
                quantity=1,
            )


class TestInventoryAdjustmentCreate:
    def test_valid(self) -> None:
        from models import InventoryAdjustmentCreate

        m = InventoryAdjustmentCreate(quantity_change=-5)
        assert m.quantity_change == -5
        assert m.reason == "other"

    def test_quantity_change_zero(self) -> None:
        """quantity_change has no ge/gt constraint — any float is allowed."""
        from models import InventoryAdjustmentCreate

        m = InventoryAdjustmentCreate(quantity_change=0)
        assert m.quantity_change == 0

    def test_reason_max_length(self) -> None:
        from models import InventoryAdjustmentCreate

        with pytest.raises(ValidationError):
            InventoryAdjustmentCreate(
                quantity_change=10,
                reason="x" * 101,
            )

    def test_reference_id_max_length(self) -> None:
        from models import InventoryAdjustmentCreate

        with pytest.raises(ValidationError):
            InventoryAdjustmentCreate(
                quantity_change=10,
                reference_id="x" * 256,
            )


class TestProductCreate:
    def test_valid(self) -> None:
        from models import ProductCreate

        m = ProductCreate(name="Wireless Mouse")
        assert m.name == "Wireless Mouse"
        assert m.price == 0
        assert m.cost == 0
        assert m.quantity_on_hand == 0
        assert m.active is True

    def test_name_too_short(self) -> None:
        from models import ProductCreate

        with pytest.raises(ValidationError):
            ProductCreate(name="")

    def test_price_negative(self) -> None:
        from models import ProductCreate

        with pytest.raises(ValidationError):
            ProductCreate(name="Mouse", price=-1)

    def test_quantity_on_hand_negative(self) -> None:
        from models import ProductCreate

        with pytest.raises(ValidationError):
            ProductCreate(name="Mouse", quantity_on_hand=-1)

    def test_min_stock_negative(self) -> None:
        from models import ProductCreate

        with pytest.raises(ValidationError):
            ProductCreate(name="Mouse", min_stock=-0.01)


class TestProductQuantityUpdate:
    def test_valid(self) -> None:
        from models import ProductQuantityUpdate

        m = ProductQuantityUpdate(quantity_on_hand=50)
        assert m.quantity_on_hand == 50

    def test_negative_raises(self) -> None:
        from models import ProductQuantityUpdate

        with pytest.raises(ValidationError):
            ProductQuantityUpdate(quantity_on_hand=-1)
