"""Unit tests for server/models.py — Pydantic request/response models.

Tests validation rules enforced by Pydantic fields including:
  - min_length / max_length on string fields
  - regex pattern validation (report_type, field_type, frequency, etc.)
  - numeric constraints (ge, le, gt)
  - required vs optional fields and their defaults
  - BaseModel override (SanitizedModel) automatic HTML stripping
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


# ===================================================================
# SanitizedModel (BaseModel override) — HTML stripping behavior
# ===================================================================


class TestSanitizedModel:
    """The models override BaseModel = SanitizedModel for auto HTML stripping.

    String fields should have HTML tags stripped after validation.
    Fields named 'password', 'token', 'secret', 'smtp_password', and
    'twilio_auth_token' must be skipped to preserve opaque values.
    """

    def test_strips_html_from_regular_fields(self) -> None:
        from models import CustomerCreate

        m = CustomerCreate(
            first_name="<script>alert('xss')</script>Alice",
            last_name="<b>Smith</b>",
            company='<a href="evil">Acme</a>',
        )
        assert m.first_name == "alert('xss')Alice"
        assert m.last_name == "Smith"
        assert m.company == "Acme"

    def test_skips_password_field(self) -> None:
        from models import LoginRequest

        m = LoginRequest(
            email="user@example.com",
            password="<secret>abc123</secret>",
        )
        # password field is in _SKIP_SANITIZE — tags preserved
        assert m.password == "<secret>abc123</secret>"

    def test_skips_token_field(self) -> None:
        from models import ResetPasswordRequest

        m = ResetPasswordRequest(
            password="newpass123",
            token="<reset-token-abc>",
        )
        assert m.token == "<reset-token-abc>"

    def test_skips_secret_field(self) -> None:
        from models import WebhookSubscriptionCreate

        m = WebhookSubscriptionCreate(
            url="https://hooks.example.com/callback",
            events="ticket.created",
            secret="<hmac-secret>",
        )
        assert m.secret == "<hmac-secret>"

    def test_strips_html_from_email_field(self) -> None:
        from models import LoginRequest

        m = LoginRequest(
            email="  user@example.com  ",
            password="validpw",
        )
        # SanitizedModel strips HTML even from email
        assert m.email == "  user@example.com  "  # no tags, no change
        # Also test with tags
        m2 = LoginRequest(email="<b>user@example.com</b>", password="validpw")
        assert m2.email == "user@example.com"

    def test_nested_model_html_stripping(self) -> None:
        """Verify HTML stripping works on nested Pydantic models."""
        from models import RecurringInvoiceRuleCreate, RecurringInvoiceLineItem

        item = RecurringInvoiceLineItem(
            description="<script>alert(1)</script>Laptop repair",
            quantity=1,
            unit_price=99.99,
        )
        assert item.description == "alert(1)Laptop repair"

        rule = RecurringInvoiceRuleCreate(
            customer_id="c-001",
            name="<em>Monthly Invoice</em>",
            frequency="monthly",
            line_items=[item],
        )
        assert rule.name == "Monthly Invoice"

    def test_strips_html_from_mail_settings(self) -> None:
        """smtp_password is in _SKIP_SANITIZE but other fields should be stripped."""
        from models import MailSettingsUpdate

        m = MailSettingsUpdate(
            smtp_host="<b>smtp.example.com</b>",
            smtp_port=587,
            smtp_user="<i>bot@example.com</i>",
            smtp_password="<super-secret>",
            smtp_from_email="noreply@example.com",
        )
        assert m.smtp_host == "smtp.example.com"
        assert m.smtp_user == "bot@example.com"
        # smtp_password is in _SKIP_SANITIZE
        assert m.smtp_password == "<super-secret>"


# ===================================================================
# Auth models
# ===================================================================


class TestLoginRequest:
    def test_valid(self) -> None:
        from models import LoginRequest

        m = LoginRequest(email="user@example.com", password="secret123")
        assert m.email == "user@example.com"
        assert m.password == "secret123"

    def test_missing_email_raises(self) -> None:
        from models import LoginRequest

        with pytest.raises(ValidationError, match="email"):
            LoginRequest(password="secret123")

    def test_missing_password_raises(self) -> None:
        from models import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com")

    def test_email_too_short(self) -> None:
        from models import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(email="ab", password="ok")

    def test_email_too_long(self) -> None:
        from models import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(email="a" * 256, password="ok")

    def test_password_too_long(self) -> None:
        from models import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com", password="x" * 256)


class TestSetPasswordRequest:
    def test_valid(self) -> None:
        from models import SetPasswordRequest

        m = SetPasswordRequest(password="abc12345")
        assert m.password == "abc12345"

    def test_password_too_short(self) -> None:
        from models import SetPasswordRequest

        with pytest.raises(ValidationError):
            SetPasswordRequest(password="abc")

    def test_password_too_long(self) -> None:
        from models import SetPasswordRequest

        with pytest.raises(ValidationError):
            SetPasswordRequest(password="x" * 256)

    def test_empty_password_raises(self) -> None:
        from models import SetPasswordRequest

        with pytest.raises(ValidationError):
            SetPasswordRequest(password="")

    def test_missing_password_raises(self) -> None:
        from models import SetPasswordRequest

        with pytest.raises(ValidationError):
            SetPasswordRequest()


class TestPortalSetPassword:
    def test_valid(self) -> None:
        from models import PortalSetPassword

        m = PortalSetPassword(password="abcdefg")
        assert m.password == "abcdefg"

    def test_password_too_short(self) -> None:
        """PortalSetPassword requires min_length=6 (stricter than SetPasswordRequest)."""
        from models import PortalSetPassword

        with pytest.raises(ValidationError):
            PortalSetPassword(password="abcde")

    def test_missing_password_raises(self) -> None:
        from models import PortalSetPassword

        with pytest.raises(ValidationError):
            PortalSetPassword()

    def test_html_not_stripped(self) -> None:
        """password is in _SKIP_SANITIZE."""
        from models import PortalSetPassword

        m = PortalSetPassword(password="<secret>abc</secret>def")
        assert m.password == "<secret>abc</secret>def"


class TestForgotPasswordRequest:
    def test_valid(self) -> None:
        from models import ForgotPasswordRequest

        m = ForgotPasswordRequest(email="user@example.com")
        assert m.email == "user@example.com"

    def test_email_too_short(self) -> None:
        from models import ForgotPasswordRequest

        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="ab")

    def test_missing_email_raises(self) -> None:
        from models import ForgotPasswordRequest

        with pytest.raises(ValidationError):
            ForgotPasswordRequest()


class TestResetPasswordRequest:
    def test_valid(self) -> None:
        from models import ResetPasswordRequest

        m = ResetPasswordRequest(password="newpass123", token="reset-abc-123")
        assert m.password == "newpass123"
        assert m.token == "reset-abc-123"

    def test_password_too_short(self) -> None:
        """ResetPasswordRequest requires min_length=6."""
        from models import ResetPasswordRequest

        with pytest.raises(ValidationError):
            ResetPasswordRequest(password="abcde", token="valid-token")

    def test_empty_token_raises(self) -> None:
        from models import ResetPasswordRequest

        with pytest.raises(ValidationError):
            ResetPasswordRequest(password="newpass123", token="")

    def test_missing_token_raises(self) -> None:
        from models import ResetPasswordRequest

        with pytest.raises(ValidationError):
            ResetPasswordRequest(password="newpass123")


# ===================================================================
# Customer models
# ===================================================================


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


# ===================================================================
# Ticket models
# ===================================================================


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


# ===================================================================
# Invoice models
# ===================================================================


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


# ===================================================================
# Payment model
# ===================================================================


class TestPaymentCreate:
    def test_valid(self) -> None:
        from models import PaymentCreate

        m = PaymentCreate(
            invoice_id="inv-001",
            customer_id="c-001",
            amount=150.00,
        )
        assert m.invoice_id == "inv-001"
        assert m.customer_id == "c-001"
        assert m.amount == 150.00
        assert m.method == "cash"
        assert m.currency == "USD"

    def test_amount_zero_raises(self) -> None:
        """PaymentCreate amount has gt=0 (strictly greater than zero)."""
        from models import PaymentCreate

        with pytest.raises(ValidationError):
            PaymentCreate(
                invoice_id="inv-001",
                customer_id="c-001",
                amount=0,
            )

    def test_amount_negative_raises(self) -> None:
        from models import PaymentCreate

        with pytest.raises(ValidationError):
            PaymentCreate(
                invoice_id="inv-001",
                customer_id="c-001",
                amount=-50,
            )

    def test_missing_invoice_id_raises(self) -> None:
        from models import PaymentCreate

        with pytest.raises(ValidationError):
            PaymentCreate(customer_id="c-001", amount=100)

    def test_missing_customer_id_raises(self) -> None:
        from models import PaymentCreate

        with pytest.raises(ValidationError):
            PaymentCreate(invoice_id="inv-001", amount=100)

    def test_missing_amount_raises(self) -> None:
        from models import PaymentCreate

        with pytest.raises(ValidationError):
            PaymentCreate(invoice_id="inv-001", customer_id="c-001")

    def test_reference_max_length(self) -> None:
        from models import PaymentCreate

        with pytest.raises(ValidationError):
            PaymentCreate(
                invoice_id="inv-001",
                customer_id="c-001",
                amount=100,
                reference="x" * 256,
            )


# ===================================================================
# ScheduledReport — regex pattern validation
# ===================================================================


class TestScheduledReportCreate:
    def test_valid(self) -> None:
        from models import ScheduledReportCreate

        m = ScheduledReportCreate(
            name="Weekly Revenue Report",
            report_type="revenue",
            schedule_frequency="weekly",
            recipients=["admin@example.com"],
        )
        assert m.name == "Weekly Revenue Report"
        assert m.report_type == "revenue"
        assert m.schedule_frequency == "weekly"
        assert m.recipients == ["admin@example.com"]

    def test_invalid_report_type(self) -> None:
        from models import ScheduledReportCreate

        with pytest.raises(ValidationError, match="report_type"):
            ScheduledReportCreate(
                name="Bad Report",
                report_type="sales",
                schedule_frequency="weekly",
                recipients=["admin@example.com"],
            )

    def test_invalid_schedule_frequency(self) -> None:
        from models import ScheduledReportCreate

        with pytest.raises(ValidationError, match="schedule_frequency"):
            ScheduledReportCreate(
                name="Bad Report",
                report_type="revenue",
                schedule_frequency="annually",
                recipients=["admin@example.com"],
            )

    def test_valid_report_types(self) -> None:
        from models import ScheduledReportCreate

        for rtype in ("revenue", "tickets", "invoices", "appointments",
                       "tech_productivity", "customers"):
            m = ScheduledReportCreate(
                name=f"{rtype} Report",
                report_type=rtype,
                schedule_frequency="monthly",
                recipients=["a@b.com"],
            )
            assert m.report_type == rtype

    def test_valid_frequencies(self) -> None:
        from models import ScheduledReportCreate

        for freq in ("daily", "weekly", "monthly"):
            m = ScheduledReportCreate(
                name="Report",
                report_type="revenue",
                schedule_frequency=freq,
                recipients=["a@b.com"],
            )
            assert m.schedule_frequency == freq

    def test_empty_recipients_raises(self) -> None:
        """recipients has min_length=1."""
        from models import ScheduledReportCreate

        with pytest.raises(ValidationError):
            ScheduledReportCreate(
                name="Report",
                report_type="revenue",
                schedule_frequency="daily",
                recipients=[],
            )

    def test_name_too_long(self) -> None:
        from models import ScheduledReportCreate

        with pytest.raises(ValidationError):
            ScheduledReportCreate(
                name="x" * 201,
                report_type="revenue",
                schedule_frequency="daily",
                recipients=["a@b.com"],
            )

    def test_missing_name_raises(self) -> None:
        from models import ScheduledReportCreate

        with pytest.raises(ValidationError):
            ScheduledReportCreate(
                report_type="revenue",
                schedule_frequency="daily",
                recipients=["a@b.com"],
            )


class TestScheduledReportUpdate:
    def test_valid_enabled_default(self) -> None:
        from models import ScheduledReportUpdate

        m = ScheduledReportUpdate(
            name="Updated Report",
            report_type="tickets",
            schedule_frequency="weekly",
            recipients=["admin@example.com"],
        )
        assert m.enabled is True

    def test_enabled_false(self) -> None:
        from models import ScheduledReportUpdate

        m = ScheduledReportUpdate(
            name="Report",
            report_type="tickets",
            schedule_frequency="weekly",
            recipients=["admin@example.com"],
            enabled=False,
        )
        assert m.enabled is False


# ===================================================================
# Recurring Invoice — regex + numeric constraints
# ===================================================================


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

        for freq in ("daily", "weekly", "biweekly", "monthly",
                      "quarterly", "yearly"):
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


# ===================================================================
# User models — role regex
# ===================================================================


class TestUserCreate:
    def test_valid(self) -> None:
        from models import UserCreate

        m = UserCreate(name="Alice Admin", email="alice@example.com")
        assert m.name == "Alice Admin"
        assert m.email == "alice@example.com"
        assert m.role == "tech"  # default

    def test_valid_roles(self) -> None:
        from models import UserCreate

        for role in ("admin", "tech", "front_desk"):
            m = UserCreate(name="User", email="user@example.com", role=role)
            assert m.role == role

    def test_invalid_role(self) -> None:
        from models import UserCreate

        with pytest.raises(ValidationError, match="role"):
            UserCreate(name="Hacker", email="hacker@example.com", role="superadmin")

    def test_name_too_short(self) -> None:
        from models import UserCreate

        with pytest.raises(ValidationError):
            UserCreate(name="", email="a@b.com")

    def test_name_too_long(self) -> None:
        from models import UserCreate

        with pytest.raises(ValidationError):
            UserCreate(name="x" * 101, email="a@b.com")

    def test_email_too_long(self) -> None:
        from models import UserCreate

        with pytest.raises(ValidationError):
            UserCreate(name="Alice", email="x" * 256)

    def test_missing_name_raises(self) -> None:
        from models import UserCreate

        with pytest.raises(ValidationError):
            UserCreate(email="a@b.com")


class TestUserUpdate:
    def test_valid(self) -> None:
        from models import UserUpdate

        m = UserUpdate(name="Alice Updated", email="alice@new.com", role="admin")
        assert m.active is True  # default

    def test_invalid_role(self) -> None:
        from models import UserUpdate

        with pytest.raises(ValidationError):
            UserUpdate(name="Bob", email="b@b.com", role="manager")


class TestUserSettingsUpdate:
    def test_valid_theme_default(self) -> None:
        from models import UserSettingsUpdate

        m = UserSettingsUpdate()
        assert m.theme == "light"
        assert m.default_ticket_status == "new"

    def test_invalid_theme(self) -> None:
        from models import UserSettingsUpdate

        with pytest.raises(ValidationError, match="theme"):
            UserSettingsUpdate(theme="neon")

    def test_valid_themes(self) -> None:
        from models import UserSettingsUpdate

        for theme in ("light", "dark"):
            m = UserSettingsUpdate(theme=theme)
            assert m.theme == theme

    def test_default_ticket_status_max_length(self) -> None:
        from models import UserSettingsUpdate

        with pytest.raises(ValidationError):
            UserSettingsUpdate(default_ticket_status="x" * 51)


# ===================================================================
# CustomField — regex for entity_type and field_type
# ===================================================================


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

        for ftype in ("text", "number", "date", "select",
                       "multiselect", "checkbox", "textarea"):
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


# ===================================================================
# 2FA models — fixed-length digit pattern
# ===================================================================


class TestSetup2FARequest:
    def test_valid(self) -> None:
        from models import Setup2FARequest

        m = Setup2FARequest(code="123456")
        assert m.code == "123456"

    def test_code_contains_letters_raises(self) -> None:
        from models import Setup2FARequest

        with pytest.raises(ValidationError):
            Setup2FARequest(code="12345a")

    def test_code_too_short(self) -> None:
        """min_length=6, max_length=6, so 5 chars fails."""
        from models import Setup2FARequest

        with pytest.raises(ValidationError):
            Setup2FARequest(code="12345")

    def test_code_too_long(self) -> None:
        from models import Setup2FARequest

        with pytest.raises(ValidationError):
            Setup2FARequest(code="1234567")

    def test_empty_code_raises(self) -> None:
        from models import Setup2FARequest

        with pytest.raises(ValidationError):
            Setup2FARequest(code="")


class TestCompleteLoginRequest:
    def test_valid(self) -> None:
        from models import CompleteLoginRequest

        m = CompleteLoginRequest(temp_token="temp-abc", code="654321")
        assert m.temp_token == "temp-abc"
        assert m.code == "654321"

    def test_invalid_code_pattern(self) -> None:
        from models import CompleteLoginRequest

        with pytest.raises(ValidationError):
            CompleteLoginRequest(temp_token="tok", code="abcd12")

    def test_empty_temp_token_raises(self) -> None:
        from models import CompleteLoginRequest

        with pytest.raises(ValidationError):
            CompleteLoginRequest(temp_token="", code="123456")


class TestDisable2FARequest:
    def test_valid(self) -> None:
        from models import Disable2FARequest

        m = Disable2FARequest(code="000000")
        assert m.code == "000000"

    def test_invalid_code(self) -> None:
        from models import Disable2FARequest

        with pytest.raises(ValidationError):
            Disable2FARequest(code="abcdef")


# ===================================================================
# SavePaymentMethod — last4 pattern, exp_month/exp_year ranges
# ===================================================================


class TestSavePaymentMethodRequest:
    def test_valid(self) -> None:
        from models import SavePaymentMethodRequest

        m = SavePaymentMethodRequest(
            customer_id="c-001",
            stripe_payment_method_id="pm_1234567890",
            brand="Visa",
            last4="4242",
            exp_month=12,
            exp_year=2028,
        )
        assert m.last4 == "4242"
        assert m.exp_month == 12
        assert m.exp_year == 2028

    def test_invalid_last4_pattern(self) -> None:
        """last4 must match ^\\d{4}$."""
        from models import SavePaymentMethodRequest

        with pytest.raises(ValidationError, match="last4"):
            SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="abc",
                exp_month=12,
                exp_year=2028,
            )

    def test_last4_too_short(self) -> None:
        from models import SavePaymentMethodRequest

        with pytest.raises(ValidationError):
            SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="123",
                exp_month=12,
                exp_year=2028,
            )

    def test_last4_too_long(self) -> None:
        from models import SavePaymentMethodRequest

        with pytest.raises(ValidationError):
            SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="12345",
                exp_month=12,
                exp_year=2028,
            )

    def test_exp_month_too_low(self) -> None:
        from models import SavePaymentMethodRequest

        with pytest.raises(ValidationError):
            SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="4242",
                exp_month=0,
                exp_year=2028,
            )

    def test_exp_month_too_high(self) -> None:
        from models import SavePaymentMethodRequest

        with pytest.raises(ValidationError):
            SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="4242",
                exp_month=13,
                exp_year=2028,
            )

    def test_exp_year_too_low(self) -> None:
        from models import SavePaymentMethodRequest

        with pytest.raises(ValidationError):
            SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="4242",
                exp_month=12,
                exp_year=2019,
            )

    def test_exp_year_too_high(self) -> None:
        from models import SavePaymentMethodRequest

        with pytest.raises(ValidationError):
            SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="4242",
                exp_month=12,
                exp_year=2101,
            )

    def test_brand_max_length(self) -> None:
        from models import SavePaymentMethodRequest

        with pytest.raises(ValidationError):
            SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="x" * 51,
                last4="4242",
                exp_month=12,
                exp_year=2028,
            )


# ===================================================================
# StockTransfer / Inventory — gt / ge constraints
# ===================================================================


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


# ===================================================================
# Product models
# ===================================================================


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


# ===================================================================
# Purchase Order models
# ===================================================================


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


# ===================================================================
# Appointment models
# ===================================================================


class TestAppointmentCreate:
    def test_valid(self) -> None:
        from models import AppointmentCreate

        m = AppointmentCreate(
            customer_id="c-001",
            title="Fix laptop",
            start_time=1700000000,
            end_time=1700003600,
        )
        assert m.title == "Fix laptop"
        assert m.all_day is False

    def test_all_day_default(self) -> None:
        from models import AppointmentCreate

        m = AppointmentCreate(
            customer_id="c-001",
            title="All day event",
            start_time=1700000000,
            end_time=1700003600,
        )
        assert m.all_day is False

    def test_start_time_negative(self) -> None:
        from models import AppointmentCreate

        with pytest.raises(ValidationError):
            AppointmentCreate(
                customer_id="c-001",
                title="Test",
                start_time=-1,
                end_time=100,
            )

    def test_end_time_negative(self) -> None:
        from models import AppointmentCreate

        with pytest.raises(ValidationError):
            AppointmentCreate(
                customer_id="c-001",
                title="Test",
                start_time=100,
                end_time=-1,
            )

    def test_title_too_long(self) -> None:
        from models import AppointmentCreate

        with pytest.raises(ValidationError):
            AppointmentCreate(
                customer_id="c-001",
                title="x" * 501,
                start_time=100,
                end_time=200,
            )


# ===================================================================
# DayHours / BusinessHours — time pattern
# ===================================================================


class TestDayHours:
    def test_defaults(self) -> None:
        from models import DayHours

        m = DayHours()
        assert m.enabled is True
        assert m.open == "09:00"
        assert m.close == "18:00"

    def test_valid_times(self) -> None:
        from models import DayHours

        for time_str in ("00:00", "08:30", "12:00", "23:59"):
            m = DayHours(open=time_str, close=time_str)
            assert m.open == time_str

    def test_invalid_time_format(self) -> None:
        from models import DayHours

        with pytest.raises(ValidationError, match="open"):
            DayHours(open="9:00")

    def test_invalid_time_format_no_leading_zero(self) -> None:
        from models import DayHours

        with pytest.raises(ValidationError):
            DayHours(close="9:00")

    def test_invalid_time_no_colon(self) -> None:
        from models import DayHours

        with pytest.raises(ValidationError):
            DayHours(open="0900")


class TestBusinessHoursUpdate:
    def test_defaults(self) -> None:
        from models import BusinessHoursUpdate

        m = BusinessHoursUpdate()
        assert m.monday.enabled is True
        assert m.monday.open == "09:00"
        assert m.saturday.enabled is False
        assert m.sunday.enabled is False


# ===================================================================
# TaxRate models
# ===================================================================


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


# ===================================================================
# Estimate models
# ===================================================================


class TestEstimateCreate:
    def test_valid(self) -> None:
        from models import EstimateCreate

        m = EstimateCreate(customer_id="c-001")
        assert m.customer_id == "c-001"
        assert m.currency == "USD"
        assert m.tax_rate == 0

    def test_tax_rate_negative(self) -> None:
        from models import EstimateCreate

        with pytest.raises(ValidationError):
            EstimateCreate(customer_id="c-001", tax_rate=-1)

    def test_tax_rate_too_high(self) -> None:
        from models import EstimateCreate

        with pytest.raises(ValidationError):
            EstimateCreate(customer_id="c-001", tax_rate=101)

    def test_discount_amount_negative(self) -> None:
        from models import EstimateCreate

        with pytest.raises(ValidationError):
            EstimateCreate(customer_id="c-001", discount_amount=-0.01)


# ===================================================================
# Tenant models
# ===================================================================


class TestTenantCreate:
    def test_valid(self) -> None:
        from models import TenantCreate

        m = TenantCreate(name="Acme Repair")
        assert m.name == "Acme Repair"
        assert m.slug == ""

    def test_empty_name_raises(self) -> None:
        from models import TenantCreate

        with pytest.raises(ValidationError):
            TenantCreate(name="")


class TestTenantMemberAdd:
    def test_valid(self) -> None:
        from models import TenantMemberAdd

        m = TenantMemberAdd(username="alice")
        assert m.username == "alice"
        assert m.role == "user"

    def test_empty_username_raises(self) -> None:
        from models import TenantMemberAdd

        with pytest.raises(ValidationError):
            TenantMemberAdd(username="")


# ===================================================================
# Webhook models
# ===================================================================


class TestWebhookSubscriptionCreate:
    def test_valid(self) -> None:
        from models import WebhookSubscriptionCreate

        m = WebhookSubscriptionCreate(
            url="https://hooks.example.com/callback",
            events="ticket.created",
        )
        assert m.url == "https://hooks.example.com/callback"
        assert m.events == "ticket.created"

    def test_url_too_short(self) -> None:
        """min_length=5."""
        from models import WebhookSubscriptionCreate

        with pytest.raises(ValidationError):
            WebhookSubscriptionCreate(url="http", events="e")

    def test_url_too_long(self) -> None:
        from models import WebhookSubscriptionCreate

        with pytest.raises(ValidationError):
            WebhookSubscriptionCreate(url="x" * 2001, events="e")

    def test_events_empty_raises(self) -> None:
        from models import WebhookSubscriptionCreate

        with pytest.raises(ValidationError):
            WebhookSubscriptionCreate(url="https://example.com/hook", events="")


# ===================================================================
# Mail/SMS settings
# ===================================================================


class TestMailSettingsUpdate:
    def test_valid(self) -> None:
        from models import MailSettingsUpdate

        m = MailSettingsUpdate()
        assert m.smtp_port == 587
        assert m.smtp_tls is True
        assert m.enabled is False

    def test_smtp_port_too_low(self) -> None:
        from models import MailSettingsUpdate

        with pytest.raises(ValidationError):
            MailSettingsUpdate(smtp_port=0)

    def test_smtp_port_too_high(self) -> None:
        from models import MailSettingsUpdate

        with pytest.raises(ValidationError):
            MailSettingsUpdate(smtp_port=65536)

    def test_smtp_host_max_length(self) -> None:
        from models import MailSettingsUpdate

        with pytest.raises(ValidationError):
            MailSettingsUpdate(smtp_host="x" * 256)


# ===================================================================
# Portal — minimal coverage
# ===================================================================


class TestPortalLoginRequest:
    def test_valid(self) -> None:
        from models import PortalLoginRequest

        m = PortalLoginRequest(email="user@portal.com", password="abc123")
        assert m.email == "user@portal.com"


class TestPortalNoteCreate:
    def test_valid(self) -> None:
        from models import PortalNoteCreate

        m = PortalNoteCreate(content="Customer note")
        assert m.content == "Customer note"

    def test_content_too_long(self) -> None:
        from models import PortalNoteCreate

        with pytest.raises(ValidationError):
            PortalNoteCreate(content="x" * 5001)


class TestPortalPaymentCreate:
    def test_valid(self) -> None:
        from models import PortalPaymentCreate

        m = PortalPaymentCreate(invoice_id="inv-001", amount=99.99)
        assert m.method == "card"

    def test_amount_zero_raises(self) -> None:
        from models import PortalPaymentCreate

        with pytest.raises(ValidationError):
            PortalPaymentCreate(invoice_id="inv-001", amount=0)


# ===================================================================
# POS models
# ===================================================================


class TestPOSCreate:
    def test_valid(self) -> None:
        from models import POSCreate

        m = POSCreate()
        assert m.customer_name == "Walk-in"
        assert m.payment_method == "cash"

    def test_invalid_payment_method(self) -> None:
        from models import POSCreate

        with pytest.raises(ValidationError, match="payment_method"):
            POSCreate(payment_method="check")

    def test_valid_payment_methods(self) -> None:
        from models import POSCreate

        for method in ("cash", "card", "invoice"):
            m = POSCreate(payment_method=method)
            assert m.payment_method == method

    def test_discount_amount_negative(self) -> None:
        from models import POSCreate

        with pytest.raises(ValidationError):
            POSCreate(discount_amount=-1)


class TestPOSAddItem:
    def test_valid(self) -> None:
        from models import POSAddItem

        m = POSAddItem(
            sale_id="sale-001",
            product_id="prod-001",
            product_name="USB Cable",
            quantity=2,
            unit_price=9.99,
        )
        assert m.quantity == 2

    def test_quantity_zero_raises(self) -> None:
        """POSAddItem.quantity has gt=0."""
        from models import POSAddItem

        with pytest.raises(ValidationError):
            POSAddItem(
                sale_id="sale-001",
                product_id="prod-001",
                product_name="Cable",
                quantity=0,
                unit_price=5,
            )

    def test_unit_price_negative_raises(self) -> None:
        from models import POSAddItem

        with pytest.raises(ValidationError):
            POSAddItem(
                sale_id="sale-001",
                product_id="prod-001",
                product_name="Cable",
                quantity=1,
                unit_price=-5,
            )


# ===================================================================
# SetPin / PosLogin — regex patterns
# ===================================================================


class TestSetPinRequest:
    def test_valid_pin(self) -> None:
        from models import SetPinRequest

        m = SetPinRequest(pin="1234")
        assert m.pin == "1234"

    def test_empty_pin_default(self) -> None:
        from models import SetPinRequest

        m = SetPinRequest()
        assert m.pin == ""

    def test_pin_with_letters_raises(self) -> None:
        """Pattern is ^\\d{0,10}$."""
        from models import SetPinRequest

        with pytest.raises(ValidationError):
            SetPinRequest(pin="abcd")

    def test_pin_too_long(self) -> None:
        from models import SetPinRequest

        with pytest.raises(ValidationError):
            SetPinRequest(pin="12345678901")


class TestPosLoginRequest:
    def test_valid(self) -> None:
        from models import PosLoginRequest

        m = PosLoginRequest(user_id="u-001", pin="1234")
        assert m.pin == "1234"

    def test_pin_too_short(self) -> None:
        """min_length=4 for PosLoginRequest."""
        from models import PosLoginRequest

        with pytest.raises(ValidationError):
            PosLoginRequest(user_id="u-001", pin="123")

    def test_pin_too_long(self) -> None:
        from models import PosLoginRequest

        with pytest.raises(ValidationError):
            PosLoginRequest(user_id="u-001", pin="12345678901")

    def test_pin_with_letters_raises(self) -> None:
        from models import PosLoginRequest

        with pytest.raises(ValidationError):
            PosLoginRequest(user_id="u-001", pin="12a4")
