"""Ticket models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestTicketCreate:
    def test_valid(self) -> None:
        from models import TicketCreate

        m = TicketCreate(customer_id="c-001", title="Fix printer")
        assert m.customer_id == "c-001"
        assert m.title == "Fix printer"
        assert m.priority == "normal"  # default

    def test_missing_customer_id_raises(self) -> None:
        from models import TicketCreate

        with pytest.raises(ValidationError):
            TicketCreate(title="Fix printer")

    def test_missing_title_raises(self) -> None:
        from models import TicketCreate

        with pytest.raises(ValidationError):
            TicketCreate(customer_id="c-001")

    def test_title_too_long(self) -> None:
        from models import TicketCreate

        with pytest.raises(ValidationError):
            TicketCreate(customer_id="c-001", title="x" * 501)

    def test_description_max_length(self) -> None:
        from models import TicketCreate

        with pytest.raises(ValidationError):
            TicketCreate(
                customer_id="c-001",
                title="Fix printer",
                description="x" * 5001,
            )

    def test_defaults_applied(self) -> None:
        from models import TicketCreate

        m = TicketCreate(customer_id="c-001", title="Fix")
        assert m.description == ""
        assert m.device_type == ""
        assert m.device_model == ""
        assert m.device_serial == ""
        assert m.device_imei == ""
        assert m.device_password == ""
        assert m.priority == "normal"

    def test_priority_custom_value(self) -> None:
        from models import TicketCreate

        m = TicketCreate(customer_id="c-001", title="Fix", priority="high")
        assert m.priority == "high"


class TestTicketNoteCreate:
    def test_valid(self) -> None:
        from models import TicketNoteCreate

        m = TicketNoteCreate(content="This is a note about the ticket.")
        assert m.content == "This is a note about the ticket."
        assert m.internal is False
        assert m.author == ""

    def test_internal_default_false(self) -> None:
        from models import TicketNoteCreate

        m = TicketNoteCreate(content="Internal note")
        assert m.internal is False

    def test_internal_true(self) -> None:
        from models import TicketNoteCreate

        m = TicketNoteCreate(content="Internal note", internal=True)
        assert m.internal is True

    def test_content_too_long(self) -> None:
        from models import TicketNoteCreate

        with pytest.raises(ValidationError):
            TicketNoteCreate(content="x" * 5001)

    def test_empty_content_raises(self) -> None:
        from models import TicketNoteCreate

        with pytest.raises(ValidationError):
            TicketNoteCreate(content="")

    def test_missing_content_raises(self) -> None:
        from models import TicketNoteCreate

        with pytest.raises(ValidationError):
            TicketNoteCreate()

    def test_author_max_length(self) -> None:
        from models import TicketNoteCreate

        with pytest.raises(ValidationError):
            TicketNoteCreate(content="Hello", author="x" * 201)


class TestTicketStatusUpdate:
    def test_valid(self) -> None:
        from models import TicketStatusUpdate

        m = TicketStatusUpdate(status="in_progress")
        assert m.status == "in_progress"

    def test_empty_status_raises(self) -> None:
        from models import TicketStatusUpdate

        with pytest.raises(ValidationError):
            TicketStatusUpdate(status="")

    def test_status_too_long(self) -> None:
        from models import TicketStatusUpdate

        with pytest.raises(ValidationError):
            TicketStatusUpdate(status="x" * 51)


class TestTicketAssign:
    def test_valid(self) -> None:
        from models import TicketAssign

        m = TicketAssign(assigned_user_id="u-042")
        assert m.assigned_user_id == "u-042"

    def test_empty_id_raises(self) -> None:
        from models import TicketAssign

        with pytest.raises(ValidationError):
            TicketAssign(assigned_user_id="")
