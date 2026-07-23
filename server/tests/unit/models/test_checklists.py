"""Checklist template models — name/description/item validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestChecklistTemplateCreate:
    """ChecklistTemplateCreate — name is required, min_length=1."""

    def test_valid(self) -> None:
        from models import ChecklistTemplateCreate

        m = ChecklistTemplateCreate(name="Safety Checklist")
        assert m.name == "Safety Checklist"
        assert m.description == ""
        assert m.items == []

    def test_valid_with_all_fields(self) -> None:
        from models import ChecklistTemplateCreate

        m = ChecklistTemplateCreate(
            name="Pre-flight",
            description="Before departure checks",
            items=[{"label": "Seat belts", "sort_order": 1}],
        )
        assert m.name == "Pre-flight"
        assert m.description == "Before departure checks"
        assert m.items == [{"label": "Seat belts", "sort_order": 1}]

    def test_name_too_short(self) -> None:
        from models import ChecklistTemplateCreate

        with pytest.raises(ValidationError):
            ChecklistTemplateCreate(name="")

    def test_name_exceeds_max_length(self) -> None:
        from models import ChecklistTemplateCreate

        with pytest.raises(ValidationError):
            ChecklistTemplateCreate(name="x" * 256)

    def test_description_exceeds_max_length(self) -> None:
        from models import ChecklistTemplateCreate

        with pytest.raises(ValidationError):
            ChecklistTemplateCreate(name="OK", description="x" * 2001)

    def test_empty_items_allowed(self) -> None:
        from models import ChecklistTemplateCreate

        m = ChecklistTemplateCreate(name="Empty", items=[])
        assert m.items == []


class TestChecklistTemplateUpdate:
    """ChecklistTemplateUpdate — same structure as Create."""

    def test_valid(self) -> None:
        from models import ChecklistTemplateUpdate

        m = ChecklistTemplateUpdate(name="Updated Checklist")
        assert m.name == "Updated Checklist"
        assert m.description == ""
        assert m.items == []

    def test_valid_with_items(self) -> None:
        from models import ChecklistTemplateUpdate

        items = [{"label": "Step 1", "sort_order": 1}, {"label": "Step 2"}]
        m = ChecklistTemplateUpdate(
            name="Steps",
            description="Step-by-step",
            items=items,
        )
        assert m.items == items

    def test_name_too_short(self) -> None:
        from models import ChecklistTemplateUpdate

        with pytest.raises(ValidationError):
            ChecklistTemplateUpdate(name="")

    def test_name_exceeds_max_length(self) -> None:
        from models import ChecklistTemplateUpdate

        with pytest.raises(ValidationError):
            ChecklistTemplateUpdate(name="x" * 256)


class TestChecklistApply:
    """ChecklistApply — template_id is required, min_length=1."""

    def test_valid(self) -> None:
        from models import ChecklistApply

        m = ChecklistApply(template_id="ct-12345")
        assert m.template_id == "ct-12345"

    def test_template_id_too_short(self) -> None:
        from models import ChecklistApply

        with pytest.raises(ValidationError):
            ChecklistApply(template_id="")

    def test_template_id_missing(self) -> None:
        from models import ChecklistApply

        with pytest.raises(ValidationError):
            ChecklistApply()  # type: ignore[call-arg]


class TestChecklistToggle:
    """ChecklistToggle — completed defaults to False."""

    def test_default_not_completed(self) -> None:
        from models import ChecklistToggle

        m = ChecklistToggle()
        assert m.completed is False

    def test_completed_true(self) -> None:
        from models import ChecklistToggle

        m = ChecklistToggle(completed=True)
        assert m.completed is True

    def test_completed_false(self) -> None:
        from models import ChecklistToggle

        m = ChecklistToggle(completed=False)
        assert m.completed is False

    def test_invalid_type(self) -> None:
        from models import ChecklistToggle

        # Pydantic coerces truthy strings to True for bool fields
        m = ChecklistToggle(completed="yes")  # type: ignore[arg-type]
        assert m.completed is True
