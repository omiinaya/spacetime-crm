"""Recurring Invoice — regex + numeric constraints."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestRecurringInvoiceRuleCreate:
    def test_valid(self) -> None:
        from models import RecurringInvoiceRuleCreate

        m = RecurringInvoiceRuleCreate(
            customer_id="c-001",
            name="Monthly maint",
            frequency="monthly",
        )
        assert m.customer_id == "c-001"
        assert m.name == "Monthly maint"
        assert m.frequency == "monthly"
        assert m.interval_count == 1
        assert m.due_date_days == 30

    def test_invalid_frequency(self) -> None:
        from models import RecurringInvoiceRuleCreate

        with pytest.raises(ValidationError, match="frequency"):
            RecurringInvoiceRuleCreate(
                customer_id="c-001",
                name="Bad",
                frequency="fortnightly",
            )

    def test_valid_frequencies(self) -> None:
        from models import RecurringInvoiceRuleCreate

        for freq in ("daily", "weekly", "biweekly", "monthly", "quarterly", "yearly"):
            m = RecurringInvoiceRuleCreate(
                customer_id="c-001",
                name=freq,
                frequency=freq,
            )
            assert m.frequency == freq

    def test_interval_count_too_low(self) -> None:
        """interval_count has ge=1."""
        from models import RecurringInvoiceRuleCreate

        # default is 1 (valid), explicit 0 should fail
        with pytest.raises(ValidationError):
            RecurringInvoiceRuleCreate(
                customer_id="c-001",
                name="Bad",
                frequency="monthly",
                interval_count=0,
            )

    def test_interval_count_too_high(self) -> None:
        """interval_count has le=365."""
        from models import RecurringInvoiceRuleCreate

        with pytest.raises(ValidationError):
            RecurringInvoiceRuleCreate(
                customer_id="c-001",
                name="Bad",
                frequency="monthly",
                interval_count=366,
            )

    def test_due_date_days_too_high(self) -> None:
        """due_date_days has le=365."""
        from models import RecurringInvoiceRuleCreate

        with pytest.raises(ValidationError):
            RecurringInvoiceRuleCreate(
                customer_id="c-001",
                name="Bad",
                frequency="monthly",
                due_date_days=366,
            )

    def test_due_date_days_negative_raises(self) -> None:
        from models import RecurringInvoiceRuleCreate

        with pytest.raises(ValidationError):
            RecurringInvoiceRuleCreate(
                customer_id="c-001",
                name="Bad",
                frequency="monthly",
                due_date_days=-1,
            )

    def test_line_items_valid(self) -> None:
        from models import RecurringInvoiceRuleCreate, RecurringInvoiceLineItem

        items = [
            RecurringInvoiceLineItem(
                description="Service fee",
                quantity=1,
                unit_price=100.00,
            ),
        ]
        m = RecurringInvoiceRuleCreate(
            customer_id="c-001",
            name="Monthly",
            frequency="monthly",
            line_items=items,
        )
        assert len(m.line_items) == 1
        assert m.line_items[0].description == "Service fee"


class TestRecurringInvoiceRuleUpdate:
    def test_valid(self) -> None:
        from models import RecurringInvoiceRuleUpdate

        m = RecurringInvoiceRuleUpdate(
            name="Updated Rule",
            frequency="quarterly",
        )
        assert m.status == "active"  # default

    def test_invalid_status(self) -> None:
        from models import RecurringInvoiceRuleUpdate

        with pytest.raises(ValidationError, match="status"):
            RecurringInvoiceRuleUpdate(
                name="Rule",
                frequency="monthly",
                status="deleted",
            )

    def test_valid_statuses(self) -> None:
        from models import RecurringInvoiceRuleUpdate

        for status in ("active", "paused", "cancelled"):
            m = RecurringInvoiceRuleUpdate(
                name="Rule",
                frequency="monthly",
                status=status,
            )
            assert m.status == status
