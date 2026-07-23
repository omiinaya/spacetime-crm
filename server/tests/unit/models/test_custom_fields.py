"""CustomField — regex for entity_type and field_type."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestCustomFieldDefinitionCreate:
    def test_valid(self) -> None:
        from models import CustomFieldDefinitionCreate

        m = CustomFieldDefinitionCreate(
            entity_type="customer",
            label="VIP Status",
            field_type="select",
        )
        assert m.entity_type == "customer"
        assert m.label == "VIP Status"
        assert m.field_type == "select"
        assert m.sort_order == 0
        assert m.required is False

    def test_invalid_entity_type(self) -> None:
        from models import CustomFieldDefinitionCreate

        with pytest.raises(ValidationError, match="entity_type"):
            CustomFieldDefinitionCreate(
                entity_type="order",
                label="Bad",
                field_type="text",
            )

    def test_valid_entity_types(self) -> None:
        from models import CustomFieldDefinitionCreate

        for etype in ("customer", "ticket", "invoice", "product"):
            m = CustomFieldDefinitionCreate(
                entity_type=etype,
                label="Test",
                field_type="text",
            )
            assert m.entity_type == etype

    def test_invalid_field_type(self) -> None:
        from models import CustomFieldDefinitionCreate

        with pytest.raises(ValidationError, match="field_type"):
            CustomFieldDefinitionCreate(
                entity_type="customer",
                label="Bad",
                field_type="toggle",
            )

    def test_valid_field_types(self) -> None:
        from models import CustomFieldDefinitionCreate

        for ftype in (
            "text",
            "number",
            "date",
            "select",
            "multiselect",
            "checkbox",
            "textarea",
        ):
            m = CustomFieldDefinitionCreate(
                entity_type="customer",
                label="Test",
                field_type=ftype,
            )
            assert m.field_type == ftype

    def test_label_too_short(self) -> None:
        from models import CustomFieldDefinitionCreate

        with pytest.raises(ValidationError):
            CustomFieldDefinitionCreate(
                entity_type="customer",
                label="",
                field_type="text",
            )

    def test_label_too_long(self) -> None:
        from models import CustomFieldDefinitionCreate

        with pytest.raises(ValidationError):
            CustomFieldDefinitionCreate(
                entity_type="customer",
                label="x" * 256,
                field_type="text",
            )

    def test_sort_order_negative(self) -> None:
        from models import CustomFieldDefinitionCreate

        with pytest.raises(ValidationError):
            CustomFieldDefinitionCreate(
                entity_type="customer",
                label="Test",
                field_type="text",
                sort_order=-1,
            )

    def test_options_default(self) -> None:
        from models import CustomFieldDefinitionCreate

        m = CustomFieldDefinitionCreate(
            entity_type="customer",
            label="Test",
            field_type="text",
        )
        assert m.options == []

    def test_id_default(self) -> None:
        from models import CustomFieldDefinitionCreate

        m = CustomFieldDefinitionCreate(
            entity_type="customer",
            label="Test",
            field_type="text",
        )
        assert m.id == ""
