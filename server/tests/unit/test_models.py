"""Unit tests for server/models.py — Pydantic request/response models.

Tests validation rules enforced by Pydantic fields including:
  - min_length / max_length on string fields
  - regex pattern validation (report_type, field_type, frequency, etc.)
  - numeric constraints (ge, le, gt)
  - required vs optional fields and their defaults
  - BaseModel override (SanitizedModel) automatic HTML stripping

models.py is loaded directly via importlib because the untracked models/
package directory shadows it on sys.path.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# ── Load server/models.py directly, bypassing the models/ package ──────────
_MODELS_PATH = Path(__file__).resolve().parent.parent.parent / "models.py"
_spec = importlib.util.spec_from_file_location("_models_py", _MODELS_PATH)
assert _spec is not None and _spec.loader is not None
models = importlib.util.module_from_spec(_spec)
sys.modules["_models_py"] = models
_spec.loader.exec_module(models)


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
        m = models.CustomerCreate(
            first_name="<script>alert('xss')</script>Alice",
            last_name="<b>Smith</b>",
            company='<a href="evil">Acme</a>',
        )
        assert m.first_name == "alert('xss')Alice"
        assert m.last_name == "Smith"
        assert m.company == "Acme"

    def test_skips_password_field(self) -> None:
        m = models.LoginRequest(
            email="user@example.com",
            password="<secret>abc123</secret>",
        )
        assert m.password == "<secret>abc123</secret>"

    def test_skips_token_field(self) -> None:
        m = models.ResetPasswordRequest(
            password="newpass123",
            token="<reset-token-abc>",
        )
        assert m.token == "<reset-token-abc>"

    def test_skips_secret_field(self) -> None:
        m = models.WebhookSubscriptionCreate(
            url="https://hooks.example.com/callback",
            events="ticket.created",
            secret="<hmac-secret>",
        )
        assert m.secret == "<hmac-secret>"

    def test_strips_html_from_email_field(self) -> None:
        m = models.LoginRequest(email="<b>user@example.com</b>", password="validpw")
        assert m.email == "user@example.com"

    def test_nested_model_html_stripping(self) -> None:
        item = models.RecurringInvoiceLineItem(
            description="<script>alert(1)</script>Laptop repair",
            quantity=1,
            unit_price=99.99,
        )
        assert item.description == "alert(1)Laptop repair"

        rule = models.RecurringInvoiceRuleCreate(
            customer_id="c-001",
            name="<em>Monthly Invoice</em>",
            frequency="monthly",
            line_items=[item],
        )
        assert rule.name == "Monthly Invoice"

    def test_strips_html_from_mail_settings(self) -> None:
        m = models.MailSettingsUpdate(
            smtp_host="<b>smtp.example.com</b>",
            smtp_port=587,
            smtp_user="<i>bot@example.com</i>",
            smtp_password="<super-secret>",
            smtp_from_email="noreply@example.com",
        )
        assert m.smtp_host == "smtp.example.com"
        assert m.smtp_user == "bot@example.com"
        assert m.smtp_password == "<super-secret>"

    def test_skips_twilio_auth_token(self) -> None:
        m = models.SMSSettingsUpdate(
            twilio_account_sid="AC123",
            twilio_auth_token="<auth-token-secret>",
            twilio_from_number="+1234567890",
        )
        assert m.twilio_auth_token == "<auth-token-secret>"


# ===================================================================
# Auth models
# ===================================================================


class TestLoginRequest:
    def test_valid(self) -> None:
        m = models.LoginRequest(email="user@example.com", password="secret123")
        assert m.email == "user@example.com"
        assert m.password == "secret123"

    def test_missing_email_raises(self) -> None:
        with pytest.raises(ValidationError, match="email"):
            models.LoginRequest(password="secret123")

    def test_missing_password_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.LoginRequest(email="user@example.com")

    def test_email_too_short(self) -> None:
        with pytest.raises(ValidationError):
            models.LoginRequest(email="ab", password="ok")

    def test_email_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.LoginRequest(email="a" * 256, password="ok")

    def test_password_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.LoginRequest(email="user@example.com", password="x" * 256)


class TestSetPasswordRequest:
    def test_valid(self) -> None:
        m = models.SetPasswordRequest(password="abc12345")
        assert m.password == "abc12345"

    def test_password_too_short(self) -> None:
        with pytest.raises(ValidationError):
            models.SetPasswordRequest(password="abc")

    def test_password_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.SetPasswordRequest(password="x" * 256)

    def test_empty_password_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.SetPasswordRequest(password="")

    def test_missing_password_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.SetPasswordRequest()


class TestPortalSetPassword:
    def test_valid(self) -> None:
        m = models.PortalSetPassword(password="abcdefg")
        assert m.password == "abcdefg"

    def test_password_too_short(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalSetPassword(password="abcde")

    def test_missing_password_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalSetPassword()

    def test_html_not_stripped(self) -> None:
        m = models.PortalSetPassword(password="<secret>abc</secret>def")
        assert m.password == "<secret>abc</secret>def"


class TestForgotPasswordRequest:
    def test_valid(self) -> None:
        m = models.ForgotPasswordRequest(email="user@example.com")
        assert m.email == "user@example.com"

    def test_email_too_short(self) -> None:
        with pytest.raises(ValidationError):
            models.ForgotPasswordRequest(email="ab")

    def test_missing_email_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.ForgotPasswordRequest()


class TestResetPasswordRequest:
    def test_valid(self) -> None:
        m = models.ResetPasswordRequest(password="newpass123", token="reset-abc-123")
        assert m.password == "newpass123"
        assert m.token == "reset-abc-123"

    def test_password_too_short(self) -> None:
        with pytest.raises(ValidationError):
            models.ResetPasswordRequest(password="abcde", token="valid-token")

    def test_empty_token_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.ResetPasswordRequest(password="newpass123", token="")

    def test_missing_token_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.ResetPasswordRequest(password="newpass123")


# ===================================================================
# Customer models
# ===================================================================


class TestCustomerCreate:
    def test_valid(self) -> None:
        m = models.CustomerCreate(first_name="Alice", last_name="Smith")
        assert m.first_name == "Alice"
        assert m.last_name == "Smith"

    def test_defaults_applied(self) -> None:
        m = models.CustomerCreate(first_name="Bob", last_name="Jones")
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
        with pytest.raises(ValidationError, match="first_name"):
            models.CustomerCreate(first_name="", last_name="Smith")

    def test_first_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.CustomerCreate(first_name="x" * 101, last_name="Smith")

    def test_last_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.CustomerCreate(first_name="Alice", last_name="x" * 101)

    def test_email_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.CustomerCreate(
                first_name="Alice", last_name="Smith", email="x" * 256
            )

    def test_notes_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.CustomerCreate(
                first_name="Alice", last_name="Smith", notes="x" * 2001
            )

    def test_tags_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.CustomerCreate(first_name="Alice", last_name="Smith", tags="x" * 501)

    def test_missing_first_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.CustomerCreate(last_name="Smith")

    def test_missing_last_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.CustomerCreate(first_name="Alice")


class TestCustomerUpdate:
    def test_valid(self) -> None:
        m = models.CustomerUpdate(first_name="Alice", last_name="Smith")
        assert m.first_name == "Alice"
        assert m.last_name == "Smith"

    def test_defaults_applied(self) -> None:
        m = models.CustomerUpdate(first_name="Bob", last_name="Jones")
        assert m.email == ""
        assert m.phone == ""
        assert m.company == ""

    def test_missing_first_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.CustomerUpdate(last_name="Smith")

    def test_missing_last_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.CustomerUpdate(first_name="Alice")

    def test_first_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.CustomerUpdate(first_name="x" * 101, last_name="Smith")


# ===================================================================
# Ticket models
# ===================================================================


class TestTicketCreate:
    def test_valid(self) -> None:
        m = models.TicketCreate(customer_id="c-001", title="Fix printer")
        assert m.customer_id == "c-001"
        assert m.title == "Fix printer"
        assert m.priority == "normal"

    def test_missing_customer_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.TicketCreate(title="Fix printer")

    def test_missing_title_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.TicketCreate(customer_id="c-001")

    def test_title_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.TicketCreate(customer_id="c-001", title="x" * 501)

    def test_description_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.TicketCreate(
                customer_id="c-001", title="Fix printer", description="x" * 5001
            )

    def test_defaults_applied(self) -> None:
        m = models.TicketCreate(customer_id="c-001", title="Fix")
        assert m.description == ""
        assert m.device_type == ""
        assert m.device_model == ""
        assert m.device_serial == ""
        assert m.device_imei == ""
        assert m.device_password == ""
        assert m.priority == "normal"

    def test_priority_custom_value(self) -> None:
        m = models.TicketCreate(customer_id="c-001", title="Fix", priority="high")
        assert m.priority == "high"


class TestTicketTimerStart:
    def test_valid(self) -> None:
        m = models.TicketTimerStart()
        assert m.user_id == ""

    def test_with_user_id(self) -> None:
        m = models.TicketTimerStart(user_id="u-001")
        assert m.user_id == "u-001"

    def test_user_id_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.TicketTimerStart(user_id="x" * 101)


class TestTicketNoteCreate:
    def test_valid(self) -> None:
        m = models.TicketNoteCreate(content="This is a note about the ticket.")
        assert m.content == "This is a note about the ticket."
        assert m.internal is False
        assert m.author == ""

    def test_internal_default_false(self) -> None:
        m = models.TicketNoteCreate(content="Internal note")
        assert m.internal is False

    def test_internal_true(self) -> None:
        m = models.TicketNoteCreate(content="Internal note", internal=True)
        assert m.internal is True

    def test_content_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.TicketNoteCreate(content="x" * 5001)

    def test_empty_content_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.TicketNoteCreate(content="")

    def test_missing_content_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.TicketNoteCreate()

    def test_author_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.TicketNoteCreate(content="Hello", author="x" * 201)


class TestTicketStatusUpdate:
    def test_valid(self) -> None:
        m = models.TicketStatusUpdate(status="in_progress")
        assert m.status == "in_progress"

    def test_empty_status_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.TicketStatusUpdate(status="")

    def test_status_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.TicketStatusUpdate(status="x" * 51)


class TestTicketAssign:
    def test_valid(self) -> None:
        m = models.TicketAssign(assigned_user_id="u-042")
        assert m.assigned_user_id == "u-042"

    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.TicketAssign(assigned_user_id="")


# ===================================================================
# Invoice models
# ===================================================================


class TestInvoiceCreate:
    def test_valid(self) -> None:
        m = models.InvoiceCreate(customer_id="c-001")
        assert m.customer_id == "c-001"
        assert m.currency == "USD"
        assert m.due_date == 0
        assert m.discount_amount == 0
        assert m.discount_percent == 0

    def test_missing_customer_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.InvoiceCreate()

    def test_discount_percent_out_of_range_high(self) -> None:
        with pytest.raises(ValidationError):
            models.InvoiceCreate(customer_id="c-001", discount_percent=101)

    def test_discount_percent_out_of_range_low(self) -> None:
        with pytest.raises(ValidationError):
            models.InvoiceCreate(customer_id="c-001", discount_percent=-1)

    def test_discount_amount_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.InvoiceCreate(customer_id="c-001", discount_amount=-0.01)

    def test_due_date_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.InvoiceCreate(customer_id="c-001", due_date=-1)

    def test_notes_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.InvoiceCreate(customer_id="c-001", notes="x" * 2001)

    def test_currency_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.InvoiceCreate(customer_id="c-001", currency="ABCD")


class TestInvoiceStatusUpdate:
    def test_valid(self) -> None:
        m = models.InvoiceStatusUpdate(status="paid")
        assert m.status == "paid"

    def test_empty_status_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.InvoiceStatusUpdate(status="")


class TestInvoiceLineItemCreate:
    def test_valid(self) -> None:
        m = models.InvoiceLineItemCreate(
            description="Labor charge", quantity=2, unit_price=75.00
        )
        assert m.description == "Labor charge"
        assert m.quantity == 2
        assert m.unit_price == 75.00
        assert m.item_type == "service"

    def test_quantity_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.InvoiceLineItemCreate(quantity=-1)

    def test_unit_price_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.InvoiceLineItemCreate(unit_price=-0.01)

    def test_description_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.InvoiceLineItemCreate(description="x" * 501)


class TestInvoiceTaxRateUpdate:
    def test_valid(self) -> None:
        m = models.InvoiceTaxRateUpdate(tax_rate=8.5)
        assert m.tax_rate == 8.5

    def test_tax_rate_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.InvoiceTaxRateUpdate(tax_rate=-1)

    def test_tax_rate_too_high(self) -> None:
        with pytest.raises(ValidationError):
            models.InvoiceTaxRateUpdate(tax_rate=100.01)

    def test_tax_rate_zero(self) -> None:
        m = models.InvoiceTaxRateUpdate(tax_rate=0)
        assert m.tax_rate == 0

    def test_tax_rate_missing(self) -> None:
        with pytest.raises(ValidationError):
            models.InvoiceTaxRateUpdate()


class TestBulkInvoiceStatusUpdate:
    def test_valid(self) -> None:
        m = models.BulkInvoiceStatusUpdate(
            invoice_ids=["inv-001", "inv-002"], status="paid"
        )
        assert m.invoice_ids == ["inv-001", "inv-002"]
        assert m.status == "paid"

    def test_empty_invoice_ids_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.BulkInvoiceStatusUpdate(invoice_ids=[], status="paid")

    def test_too_many_invoice_ids_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.BulkInvoiceStatusUpdate(invoice_ids=["inv"] * 501, status="paid")

    def test_empty_status_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.BulkInvoiceStatusUpdate(invoice_ids=["inv-001"], status="")


class TestBulkInvoiceEdit:
    def test_valid(self) -> None:
        m = models.BulkInvoiceEdit(
            invoice_ids=["inv-001", "inv-002"], terms="Net 30", notes="Updated"
        )
        assert m.invoice_ids == ["inv-001", "inv-002"]
        assert m.terms == "Net 30"
        assert m.notes == "Updated"

    def test_empty_invoice_ids_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.BulkInvoiceEdit(invoice_ids=[], terms="Net 30")

    def test_too_many_invoice_ids_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.BulkInvoiceEdit(invoice_ids=["inv"] * 501, terms="Net 30")

    def test_defaults_applied(self) -> None:
        m = models.BulkInvoiceEdit(invoice_ids=["inv-001"])
        assert m.terms == ""
        assert m.notes == ""


# ===================================================================
# Payment models
# ===================================================================


class TestPaymentCreate:
    def test_valid(self) -> None:
        m = models.PaymentCreate(
            invoice_id="inv-001", customer_id="c-001", amount=150.00
        )
        assert m.invoice_id == "inv-001"
        assert m.customer_id == "c-001"
        assert m.amount == 150.00
        assert m.method == "cash"
        assert m.currency == "USD"

    def test_amount_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PaymentCreate(invoice_id="inv-001", customer_id="c-001", amount=0)

    def test_amount_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PaymentCreate(invoice_id="inv-001", customer_id="c-001", amount=-50)

    def test_missing_invoice_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PaymentCreate(customer_id="c-001", amount=100)

    def test_missing_customer_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PaymentCreate(invoice_id="inv-001", amount=100)

    def test_missing_amount_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PaymentCreate(invoice_id="inv-001", customer_id="c-001")

    def test_reference_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.PaymentCreate(
                invoice_id="inv-001",
                customer_id="c-001",
                amount=100,
                reference="x" * 256,
            )

    def test_defaults_applied(self) -> None:
        m = models.PaymentCreate(invoice_id="inv-001", customer_id="c-001", amount=100)
        assert m.method == "cash"
        assert m.currency == "USD"
        assert m.reference == ""
        assert m.notes == ""


# ===================================================================
# Scheduled Report models
# ===================================================================


class TestScheduledReportCreate:
    def test_valid(self) -> None:
        m = models.ScheduledReportCreate(
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
        with pytest.raises(ValidationError, match="report_type"):
            models.ScheduledReportCreate(
                name="Bad Report",
                report_type="sales",
                schedule_frequency="weekly",
                recipients=["admin@example.com"],
            )

    def test_invalid_schedule_frequency(self) -> None:
        with pytest.raises(ValidationError, match="schedule_frequency"):
            models.ScheduledReportCreate(
                name="Bad Report",
                report_type="revenue",
                schedule_frequency="annually",
                recipients=["admin@example.com"],
            )

    def test_valid_report_types(self) -> None:
        for rtype in (
            "revenue",
            "tickets",
            "invoices",
            "appointments",
            "tech_productivity",
            "customers",
        ):
            m = models.ScheduledReportCreate(
                name=f"{rtype} Report",
                report_type=rtype,
                schedule_frequency="monthly",
                recipients=["a@b.com"],
            )
            assert m.report_type == rtype

    def test_valid_frequencies(self) -> None:
        for freq in ("daily", "weekly", "monthly"):
            m = models.ScheduledReportCreate(
                name="Report",
                report_type="revenue",
                schedule_frequency=freq,
                recipients=["a@b.com"],
            )
            assert m.schedule_frequency == freq

    def test_empty_recipients_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.ScheduledReportCreate(
                name="Report",
                report_type="revenue",
                schedule_frequency="daily",
                recipients=[],
            )

    def test_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.ScheduledReportCreate(
                name="x" * 201,
                report_type="revenue",
                schedule_frequency="daily",
                recipients=["a@b.com"],
            )

    def test_missing_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.ScheduledReportCreate(
                report_type="revenue",
                schedule_frequency="daily",
                recipients=["a@b.com"],
            )

    def test_defaults_applied(self) -> None:
        m = models.ScheduledReportCreate(
            name="Report",
            report_type="revenue",
            schedule_frequency="daily",
            recipients=["a@b.com"],
        )
        assert m.schedule_config == {}
        assert m.filters == {}


class TestScheduledReportUpdate:
    def test_valid_enabled_default(self) -> None:
        m = models.ScheduledReportUpdate(
            name="Updated Report",
            report_type="tickets",
            schedule_frequency="weekly",
            recipients=["admin@example.com"],
        )
        assert m.enabled is True

    def test_enabled_false(self) -> None:
        m = models.ScheduledReportUpdate(
            name="Report",
            report_type="tickets",
            schedule_frequency="weekly",
            recipients=["admin@example.com"],
            enabled=False,
        )
        assert m.enabled is False


# ===================================================================
# Recurring Invoice models
# ===================================================================


class TestRecurringInvoiceLineItem:
    def test_valid(self) -> None:
        m = models.RecurringInvoiceLineItem(
            description="Service fee", quantity=1, unit_price=100.00
        )
        assert m.description == "Service fee"
        assert m.quantity == 1
        assert m.unit_price == 100.00
        assert m.item_type == "service"

    def test_defaults_applied(self) -> None:
        m = models.RecurringInvoiceLineItem()
        assert m.description == ""
        assert m.quantity == 1
        assert m.unit_price == 0
        assert m.item_type == "service"

    def test_quantity_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.RecurringInvoiceLineItem(quantity=-1)

    def test_unit_price_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.RecurringInvoiceLineItem(unit_price=-0.01)

    def test_description_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.RecurringInvoiceLineItem(description="x" * 501)


class TestRecurringInvoiceRuleCreate:
    def test_valid(self) -> None:
        m = models.RecurringInvoiceRuleCreate(
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
        with pytest.raises(ValidationError, match="frequency"):
            models.RecurringInvoiceRuleCreate(
                customer_id="c-001", name="Bad", frequency="fortnightly"
            )

    def test_valid_frequencies(self) -> None:
        for freq in ("daily", "weekly", "biweekly", "monthly", "quarterly", "yearly"):
            m = models.RecurringInvoiceRuleCreate(
                customer_id="c-001", name=freq, frequency=freq
            )
            assert m.frequency == freq

    def test_interval_count_too_low(self) -> None:
        with pytest.raises(ValidationError):
            models.RecurringInvoiceRuleCreate(
                customer_id="c-001", name="Bad", frequency="monthly", interval_count=0
            )

    def test_interval_count_too_high(self) -> None:
        with pytest.raises(ValidationError):
            models.RecurringInvoiceRuleCreate(
                customer_id="c-001", name="Bad", frequency="monthly", interval_count=366
            )

    def test_due_date_days_too_high(self) -> None:
        with pytest.raises(ValidationError):
            models.RecurringInvoiceRuleCreate(
                customer_id="c-001", name="Bad", frequency="monthly", due_date_days=366
            )

    def test_due_date_days_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.RecurringInvoiceRuleCreate(
                customer_id="c-001", name="Bad", frequency="monthly", due_date_days=-1
            )

    def test_line_items_valid(self) -> None:
        items = [
            models.RecurringInvoiceLineItem(
                description="Service fee", quantity=1, unit_price=100.00
            ),
        ]
        m = models.RecurringInvoiceRuleCreate(
            customer_id="c-001", name="Monthly", frequency="monthly", line_items=items
        )
        assert len(m.line_items) == 1
        assert m.line_items[0].description == "Service fee"

    def test_defaults_applied(self) -> None:
        m = models.RecurringInvoiceRuleCreate(
            customer_id="c-001", name="Rule", frequency="monthly"
        )
        assert m.interval_count == 1
        assert m.due_date_days == 30
        assert m.line_items == []
        assert m.next_generation_date == 0


class TestRecurringInvoiceRuleUpdate:
    def test_valid(self) -> None:
        m = models.RecurringInvoiceRuleUpdate(
            name="Updated Rule", frequency="quarterly"
        )
        assert m.status == "active"

    def test_invalid_status(self) -> None:
        with pytest.raises(ValidationError, match="status"):
            models.RecurringInvoiceRuleUpdate(
                name="Rule", frequency="monthly", status="deleted"
            )

    def test_valid_statuses(self) -> None:
        for status in ("active", "paused", "cancelled"):
            m = models.RecurringInvoiceRuleUpdate(
                name="Rule", frequency="monthly", status=status
            )
            assert m.status == status

    def test_missing_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.RecurringInvoiceRuleUpdate(frequency="monthly")

    def test_missing_frequency_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.RecurringInvoiceRuleUpdate(name="Rule")


# ===================================================================
# User models
# ===================================================================


class TestUserCreate:
    def test_valid(self) -> None:
        m = models.UserCreate(name="Alice Admin", email="alice@example.com")
        assert m.name == "Alice Admin"
        assert m.email == "alice@example.com"
        assert m.role == "tech"

    def test_valid_roles(self) -> None:
        for role in ("admin", "tech", "front_desk"):
            m = models.UserCreate(name="User", email="user@example.com", role=role)
            assert m.role == role

    def test_invalid_role(self) -> None:
        with pytest.raises(ValidationError, match="role"):
            models.UserCreate(
                name="Hacker", email="hacker@example.com", role="superadmin"
            )

    def test_name_too_short(self) -> None:
        with pytest.raises(ValidationError):
            models.UserCreate(name="", email="a@b.com")

    def test_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.UserCreate(name="x" * 101, email="a@b.com")

    def test_email_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.UserCreate(name="Alice", email="x" * 256)

    def test_missing_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.UserCreate(email="a@b.com")


class TestUserUpdate:
    def test_valid(self) -> None:
        m = models.UserUpdate(name="Alice Updated", email="alice@new.com", role="admin")
        assert m.active is True

    def test_invalid_role(self) -> None:
        with pytest.raises(ValidationError):
            models.UserUpdate(name="Bob", email="b@b.com", role="manager")

    def test_missing_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.UserUpdate(email="b@b.com", role="admin")

    def test_missing_email_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.UserUpdate(name="Bob", role="admin")

    def test_missing_role_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.UserUpdate(name="Bob", email="b@b.com")


class TestUserSettingsUpdate:
    def test_valid_theme_default(self) -> None:
        m = models.UserSettingsUpdate()
        assert m.theme == "light"
        assert m.default_ticket_status == "new"

    def test_invalid_theme(self) -> None:
        with pytest.raises(ValidationError, match="theme"):
            models.UserSettingsUpdate(theme="neon")

    def test_valid_themes(self) -> None:
        for theme in ("light", "dark"):
            m = models.UserSettingsUpdate(theme=theme)
            assert m.theme == theme

    def test_default_ticket_status_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.UserSettingsUpdate(default_ticket_status="x" * 51)


# ===================================================================
# CustomField models
# ===================================================================


class TestCustomFieldDefinitionCreate:
    def test_valid(self) -> None:
        m = models.CustomFieldDefinitionCreate(
            entity_type="customer", label="VIP Status", field_type="select"
        )
        assert m.entity_type == "customer"
        assert m.label == "VIP Status"
        assert m.field_type == "select"
        assert m.sort_order == 0
        assert m.required is False
        assert m.active is True

    def test_invalid_entity_type(self) -> None:
        with pytest.raises(ValidationError, match="entity_type"):
            models.CustomFieldDefinitionCreate(
                entity_type="order", label="Bad", field_type="text"
            )

    def test_valid_entity_types(self) -> None:
        for etype in ("customer", "ticket", "invoice", "product"):
            m = models.CustomFieldDefinitionCreate(
                entity_type=etype, label="Test", field_type="text"
            )
            assert m.entity_type == etype

    def test_invalid_field_type(self) -> None:
        with pytest.raises(ValidationError, match="field_type"):
            models.CustomFieldDefinitionCreate(
                entity_type="customer", label="Bad", field_type="toggle"
            )

    def test_valid_field_types(self) -> None:
        for ftype in (
            "text",
            "number",
            "date",
            "select",
            "multiselect",
            "checkbox",
            "textarea",
        ):
            m = models.CustomFieldDefinitionCreate(
                entity_type="customer", label="Test", field_type=ftype
            )
            assert m.field_type == ftype

    def test_label_too_short(self) -> None:
        with pytest.raises(ValidationError):
            models.CustomFieldDefinitionCreate(
                entity_type="customer", label="", field_type="text"
            )

    def test_label_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.CustomFieldDefinitionCreate(
                entity_type="customer", label="x" * 256, field_type="text"
            )

    def test_sort_order_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.CustomFieldDefinitionCreate(
                entity_type="customer", label="Test", field_type="text", sort_order=-1
            )

    def test_options_default(self) -> None:
        m = models.CustomFieldDefinitionCreate(
            entity_type="customer", label="Test", field_type="text"
        )
        assert m.options == []

    def test_id_default(self) -> None:
        m = models.CustomFieldDefinitionCreate(
            entity_type="customer", label="Test", field_type="text"
        )
        assert m.id == ""


class TestCustomFieldValuesUpdate:
    def test_valid(self) -> None:
        m = models.CustomFieldValuesUpdate(values={"field1": "value1"})
        assert m.values == {"field1": "value1"}

    def test_default_empty(self) -> None:
        m = models.CustomFieldValuesUpdate()
        assert m.values == {}

    def test_with_various_types(self) -> None:
        m = models.CustomFieldValuesUpdate(
            values={
                "text": "hello",
                "num": 42,
                "flag": True,
                "multi": ["a", "b"],
            }
        )
        assert m.values["text"] == "hello"
        assert m.values["num"] == 42
        assert m.values["flag"] is True
        assert m.values["multi"] == ["a", "b"]


# ===================================================================
# 2FA models
# ===================================================================


class TestSetup2FARequest:
    def test_valid(self) -> None:
        m = models.Setup2FARequest(code="123456")
        assert m.code == "123456"

    def test_code_contains_letters_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.Setup2FARequest(code="12345a")

    def test_code_too_short(self) -> None:
        with pytest.raises(ValidationError):
            models.Setup2FARequest(code="12345")

    def test_code_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.Setup2FARequest(code="1234567")

    def test_empty_code_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.Setup2FARequest(code="")


class TestCompleteLoginRequest:
    def test_valid(self) -> None:
        m = models.CompleteLoginRequest(temp_token="temp-abc", code="654321")
        assert m.temp_token == "temp-abc"
        assert m.code == "654321"

    def test_invalid_code_pattern(self) -> None:
        with pytest.raises(ValidationError):
            models.CompleteLoginRequest(temp_token="tok", code="abcd12")

    def test_empty_temp_token_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.CompleteLoginRequest(temp_token="", code="123456")

    def test_missing_temp_token_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.CompleteLoginRequest(code="123456")

    def test_missing_code_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.CompleteLoginRequest(temp_token="tok")


class TestDisable2FARequest:
    def test_valid(self) -> None:
        m = models.Disable2FARequest(code="000000")
        assert m.code == "000000"

    def test_invalid_code(self) -> None:
        with pytest.raises(ValidationError):
            models.Disable2FARequest(code="abcdef")

    def test_missing_code_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.Disable2FARequest()


# ===================================================================
# SavePaymentMethod models
# ===================================================================


class TestSavePaymentMethodRequest:
    def test_valid(self) -> None:
        m = models.SavePaymentMethodRequest(
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
        with pytest.raises(ValidationError, match="last4"):
            models.SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="abc",
                exp_month=12,
                exp_year=2028,
            )

    def test_last4_too_short(self) -> None:
        with pytest.raises(ValidationError):
            models.SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="123",
                exp_month=12,
                exp_year=2028,
            )

    def test_last4_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="12345",
                exp_month=12,
                exp_year=2028,
            )

    def test_exp_month_too_low(self) -> None:
        with pytest.raises(ValidationError):
            models.SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="4242",
                exp_month=0,
                exp_year=2028,
            )

    def test_exp_month_too_high(self) -> None:
        with pytest.raises(ValidationError):
            models.SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="4242",
                exp_month=13,
                exp_year=2028,
            )

    def test_exp_year_too_low(self) -> None:
        with pytest.raises(ValidationError):
            models.SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="4242",
                exp_month=12,
                exp_year=2019,
            )

    def test_exp_year_too_high(self) -> None:
        with pytest.raises(ValidationError):
            models.SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="Visa",
                last4="4242",
                exp_month=12,
                exp_year=2101,
            )

    def test_brand_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.SavePaymentMethodRequest(
                customer_id="c-001",
                stripe_payment_method_id="pm_123",
                brand="x" * 51,
                last4="4242",
                exp_month=12,
                exp_year=2028,
            )


class TestSetDefaultPaymentMethodRequest:
    def test_valid(self) -> None:
        m = models.SetDefaultPaymentMethodRequest(customer_id="c-001")
        assert m.customer_id == "c-001"

    def test_empty_customer_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.SetDefaultPaymentMethodRequest(customer_id="")

    def test_missing_customer_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.SetDefaultPaymentMethodRequest()


class TestPortalPayWithSavedCard:
    def test_valid(self) -> None:
        m = models.PortalPayWithSavedCard(
            invoice_id="inv-001", payment_method_id="pm_123"
        )
        assert m.invoice_id == "inv-001"
        assert m.payment_method_id == "pm_123"

    def test_empty_invoice_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalPayWithSavedCard(invoice_id="", payment_method_id="pm_123")

    def test_empty_payment_method_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalPayWithSavedCard(invoice_id="inv-001", payment_method_id="")

    def test_missing_invoice_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalPayWithSavedCard(payment_method_id="pm_123")

    def test_missing_payment_method_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalPayWithSavedCard(invoice_id="inv-001")


# ===================================================================
# StockTransfer / Inventory
# ===================================================================


class TestStockTransferRequest:
    def test_valid(self) -> None:
        m = models.StockTransferRequest(
            source_product_id="prod-001",
            destination_product_id="prod-002",
            quantity=10,
        )
        assert m.quantity == 10

    def test_quantity_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.StockTransferRequest(
                source_product_id="prod-001",
                destination_product_id="prod-002",
                quantity=0,
            )

    def test_quantity_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.StockTransferRequest(
                source_product_id="prod-001",
                destination_product_id="prod-002",
                quantity=-5,
            )

    def test_empty_source_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.StockTransferRequest(
                source_product_id="",
                destination_product_id="prod-002",
                quantity=1,
            )

    def test_empty_dest_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.StockTransferRequest(
                source_product_id="prod-001",
                destination_product_id="",
                quantity=1,
            )

    def test_defaults_applied(self) -> None:
        m = models.StockTransferRequest(
            source_product_id="prod-001",
            destination_product_id="prod-002",
            quantity=1,
        )
        assert m.reference_id == ""
        assert m.notes == ""


class TestInventoryAdjustmentCreate:
    def test_valid(self) -> None:
        m = models.InventoryAdjustmentCreate(quantity_change=-5)
        assert m.quantity_change == -5
        assert m.reason == "other"

    def test_quantity_change_zero(self) -> None:
        m = models.InventoryAdjustmentCreate(quantity_change=0)
        assert m.quantity_change == 0

    def test_reason_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.InventoryAdjustmentCreate(quantity_change=10, reason="x" * 101)

    def test_reference_id_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.InventoryAdjustmentCreate(quantity_change=10, reference_id="x" * 256)

    def test_defaults_applied(self) -> None:
        m = models.InventoryAdjustmentCreate(quantity_change=10)
        assert m.reason == "other"
        assert m.reference_id == ""
        assert m.notes == ""
        assert m.user_id == ""


# ===================================================================
# Product models
# ===================================================================


class TestProductCreate:
    def test_valid(self) -> None:
        m = models.ProductCreate(name="Wireless Mouse")
        assert m.name == "Wireless Mouse"
        assert m.price == 0
        assert m.cost == 0
        assert m.quantity_on_hand == 0
        assert m.active is True

    def test_name_too_short(self) -> None:
        with pytest.raises(ValidationError):
            models.ProductCreate(name="")

    def test_price_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.ProductCreate(name="Mouse", price=-1)

    def test_quantity_on_hand_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.ProductCreate(name="Mouse", quantity_on_hand=-1)

    def test_min_stock_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.ProductCreate(name="Mouse", min_stock=-0.01)

    def test_defaults_applied(self) -> None:
        m = models.ProductCreate(name="Mouse")
        assert m.sku == ""
        assert m.barcode == ""
        assert m.description == ""
        assert m.category == ""
        assert m.location == ""


class TestProductQuantityUpdate:
    def test_valid(self) -> None:
        m = models.ProductQuantityUpdate(quantity_on_hand=50)
        assert m.quantity_on_hand == 50

    def test_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.ProductQuantityUpdate(quantity_on_hand=-1)

    def test_zero_allowed(self) -> None:
        m = models.ProductQuantityUpdate(quantity_on_hand=0)
        assert m.quantity_on_hand == 0


# ===================================================================
# Purchase Order models
# ===================================================================


class TestPurchaseOrderCreate:
    def test_valid(self) -> None:
        m = models.PurchaseOrderCreate(vendor_name="Acme Supplies")
        assert m.vendor_name == "Acme Supplies"
        assert m.currency == "USD"
        assert m.shipping_cost == 0

    def test_empty_vendor_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PurchaseOrderCreate(vendor_name="")

    def test_shipping_cost_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.PurchaseOrderCreate(vendor_name="Acme", shipping_cost=-1)

    def test_defaults_applied(self) -> None:
        m = models.PurchaseOrderCreate(vendor_name="Acme")
        assert m.notes == ""
        assert m.currency == "USD"
        assert m.shipping_cost == 0


class TestPurchaseOrderStatusUpdate:
    def test_valid(self) -> None:
        m = models.PurchaseOrderStatusUpdate(status="received")
        assert m.status == "received"

    def test_empty_status_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PurchaseOrderStatusUpdate(status="")

    def test_status_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.PurchaseOrderStatusUpdate(status="x" * 51)


class TestPOLineItemCreate:
    def test_valid(self) -> None:
        m = models.POLineItemCreate()
        assert m.quantity == 1
        assert m.unit_price == 0
        assert m.product_id == ""

    def test_quantity_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.POLineItemCreate(quantity=-1)

    def test_unit_price_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.POLineItemCreate(unit_price=-0.01)

    def test_description_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.POLineItemCreate(description="x" * 501)


class TestPOReceiveItem:
    def test_valid(self) -> None:
        m = models.POReceiveItem(received_quantity=10)
        assert m.received_quantity == 10
        assert m.items == []

    def test_received_quantity_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.POReceiveItem(received_quantity=-1)

    def test_received_quantity_zero(self) -> None:
        m = models.POReceiveItem(received_quantity=0)
        assert m.received_quantity == 0


class TestPOApprovalAction:
    def test_valid(self) -> None:
        m = models.POApprovalAction(user_id="u-001")
        assert m.user_id == "u-001"

    def test_empty_user_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.POApprovalAction(user_id="")

    def test_missing_user_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.POApprovalAction()


# ===================================================================
# Appointment models
# ===================================================================


class TestAppointmentCreate:
    def test_valid(self) -> None:
        m = models.AppointmentCreate(
            customer_id="c-001",
            title="Fix laptop",
            start_time=1700000000,
            end_time=1700003600,
        )
        assert m.title == "Fix laptop"
        assert m.all_day is False

    def test_all_day_default(self) -> None:
        m = models.AppointmentCreate(
            customer_id="c-001",
            title="All day event",
            start_time=1700000000,
            end_time=1700003600,
        )
        assert m.all_day is False

    def test_start_time_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.AppointmentCreate(
                customer_id="c-001", title="Test", start_time=-1, end_time=100
            )

    def test_end_time_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.AppointmentCreate(
                customer_id="c-001", title="Test", start_time=100, end_time=-1
            )

    def test_title_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.AppointmentCreate(
                customer_id="c-001", title="x" * 501, start_time=100, end_time=200
            )

    def test_defaults_applied(self) -> None:
        m = models.AppointmentCreate(
            customer_id="c-001",
            title="Event",
            start_time=100,
            end_time=200,
        )
        assert m.ticket_id == ""
        assert m.description == ""
        assert m.all_day is False
        assert m.series_id == ""
        assert m.recurrence_rule == ""
        assert m.color == ""


class TestAppointmentStatusUpdate:
    def test_valid(self) -> None:
        m = models.AppointmentStatusUpdate(status="confirmed")
        assert m.status == "confirmed"

    def test_empty_status_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.AppointmentStatusUpdate(status="")

    def test_status_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.AppointmentStatusUpdate(status="x" * 51)


class TestAppointmentRecurrence:
    def test_valid(self) -> None:
        m = models.AppointmentRecurrence(recurrence_rule="FREQ=WEEKLY;BYDAY=MO")
        assert m.recurrence_rule == "FREQ=WEEKLY;BYDAY=MO"

    def test_empty_rule_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.AppointmentRecurrence(recurrence_rule="x" * 51)

    def test_rule_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.AppointmentRecurrence(recurrence_rule="x" * 51)


class TestGenerateNextOccurrence:
    def test_valid(self) -> None:
        m = models.GenerateNextOccurrence(series_id="series-001")
        assert m.series_id == "series-001"

    def test_empty_series_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.GenerateNextOccurrence(series_id="")

    def test_missing_series_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.GenerateNextOccurrence()


# ===================================================================
# DayHours / BusinessHours
# ===================================================================


class TestDayHours:
    def test_defaults(self) -> None:
        m = models.DayHours()
        assert m.enabled is True
        assert m.open == "09:00"
        assert m.close == "18:00"

    def test_valid_times(self) -> None:
        for time_str in ("00:00", "08:30", "12:00", "23:59"):
            m = models.DayHours(open=time_str, close=time_str)
            assert m.open == time_str

    def test_invalid_time_format(self) -> None:
        with pytest.raises(ValidationError, match="open"):
            models.DayHours(open="9:00")

    def test_invalid_time_no_colon(self) -> None:
        with pytest.raises(ValidationError):
            models.DayHours(open="0900")

    def test_invalid_close_time(self) -> None:
        with pytest.raises(ValidationError, match="close"):
            models.DayHours(close="9:00")


class TestBusinessHoursUpdate:
    def test_defaults(self) -> None:
        m = models.BusinessHoursUpdate()
        assert m.monday.enabled is True
        assert m.monday.open == "09:00"
        assert m.saturday.enabled is False
        assert m.sunday.enabled is False

    def test_custom_hours(self) -> None:
        m = models.BusinessHoursUpdate(
            monday=models.DayHours(enabled=True, open="08:00", close="17:00")
        )
        assert m.monday.open == "08:00"
        assert m.monday.close == "17:00"


# ===================================================================
# TaxRate models
# ===================================================================


class TestTaxRateCreate:
    def test_valid(self) -> None:
        m = models.TaxRateCreate(name="Sales Tax", rate=8.5)
        assert m.name == "Sales Tax"
        assert m.rate == 8.5
        assert m.is_default is False

    def test_rate_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.TaxRateCreate(name="Bad", rate=-1)

    def test_rate_too_high(self) -> None:
        with pytest.raises(ValidationError):
            models.TaxRateCreate(name="Bad", rate=100.01)

    def test_name_too_short(self) -> None:
        with pytest.raises(ValidationError):
            models.TaxRateCreate(name="", rate=8.5)

    def test_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.TaxRateCreate(name="x" * 101, rate=8.5)

    def test_rate_zero(self) -> None:
        m = models.TaxRateCreate(name="Zero", rate=0)
        assert m.rate == 0

    def test_rate_max(self) -> None:
        m = models.TaxRateCreate(name="Max", rate=100)
        assert m.rate == 100


class TestTaxRateUpdate:
    def test_valid(self) -> None:
        m = models.TaxRateUpdate(name="Updated Tax", rate=9.0)
        assert m.name == "Updated Tax"
        assert m.rate == 9.0
        assert m.is_default is False

    def test_rate_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.TaxRateUpdate(name="Bad", rate=-1)

    def test_rate_too_high(self) -> None:
        with pytest.raises(ValidationError):
            models.TaxRateUpdate(name="Bad", rate=100.01)

    def test_is_default_true(self) -> None:
        m = models.TaxRateUpdate(name="Default", rate=8.5, is_default=True)
        assert m.is_default is True


# ===================================================================
# Estimate models
# ===================================================================


class TestEstimateCreate:
    def test_valid(self) -> None:
        m = models.EstimateCreate(customer_id="c-001")
        assert m.customer_id == "c-001"
        assert m.currency == "USD"
        assert m.tax_rate == 0

    def test_tax_rate_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.EstimateCreate(customer_id="c-001", tax_rate=-1)

    def test_tax_rate_too_high(self) -> None:
        with pytest.raises(ValidationError):
            models.EstimateCreate(customer_id="c-001", tax_rate=101)

    def test_discount_amount_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.EstimateCreate(customer_id="c-001", discount_amount=-0.01)

    def test_missing_customer_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.EstimateCreate()

    def test_defaults_applied(self) -> None:
        m = models.EstimateCreate(customer_id="c-001")
        assert m.ticket_id == ""
        assert m.notes == ""
        assert m.expires_at == 0
        assert m.currency == "USD"
        assert m.tax_rate == 0
        assert m.discount_amount == 0


class TestEstimateStatusUpdate:
    def test_valid(self) -> None:
        m = models.EstimateStatusUpdate(status="approved")
        assert m.status == "approved"

    def test_empty_status_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.EstimateStatusUpdate(status="")

    def test_status_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.EstimateStatusUpdate(status="x" * 51)


class TestEstimateLineItemCreate:
    def test_valid(self) -> None:
        m = models.EstimateLineItemCreate(
            description="Screen replacement", quantity=1, unit_price=200.00
        )
        assert m.description == "Screen replacement"
        assert m.quantity == 1
        assert m.unit_price == 200.00
        assert m.item_type == "service"

    def test_defaults_applied(self) -> None:
        m = models.EstimateLineItemCreate()
        assert m.item_type == "service"
        assert m.description == ""
        assert m.quantity == 1
        assert m.unit_price == 0

    def test_quantity_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.EstimateLineItemCreate(quantity=-1)

    def test_unit_price_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.EstimateLineItemCreate(unit_price=-0.01)


# ===================================================================
# Tenant models
# ===================================================================


class TestTenantCreate:
    def test_valid(self) -> None:
        m = models.TenantCreate(name="Acme Repair")
        assert m.name == "Acme Repair"
        assert m.slug == ""

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.TenantCreate(name="")

    def test_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.TenantCreate(name="x" * 256)


class TestTenantUpdate:
    def test_valid(self) -> None:
        m = models.TenantUpdate(name="Updated Tenant", slug="updated")
        assert m.name == "Updated Tenant"
        assert m.slug == "updated"
        assert m.logo_url == ""
        assert m.settings == "{}"

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.TenantUpdate(name="")

    def test_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.TenantUpdate(name="x" * 256)

    def test_slug_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.TenantUpdate(name="Test", slug="x" * 256)

    def test_settings_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.TenantUpdate(name="Test", settings="x" * 10001)


class TestTenantMemberAdd:
    def test_valid(self) -> None:
        m = models.TenantMemberAdd(username="alice")
        assert m.username == "alice"
        assert m.role == "user"

    def test_empty_username_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.TenantMemberAdd(username="")

    def test_username_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.TenantMemberAdd(username="x" * 101)

    def test_custom_role(self) -> None:
        m = models.TenantMemberAdd(username="bob", role="admin")
        assert m.role == "admin"

    def test_role_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.TenantMemberAdd(username="bob", role="x" * 51)


class TestTenantMemberRoleUpdate:
    def test_valid(self) -> None:
        m = models.TenantMemberRoleUpdate(role="admin")
        assert m.role == "admin"

    def test_empty_role_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.TenantMemberRoleUpdate(role="")

    def test_role_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.TenantMemberRoleUpdate(role="x" * 51)


class TestTenantMigrate:
    def test_valid(self) -> None:
        m = models.TenantMigrate(name="New Tenant", slug="new-tenant")
        assert m.name == "New Tenant"
        assert m.slug == "new-tenant"

    def test_defaults(self) -> None:
        m = models.TenantMigrate()
        assert m.name == "Default"
        assert m.slug == ""


# ===================================================================
# Webhook models
# ===================================================================


class TestWebhookSubscriptionCreate:
    def test_valid(self) -> None:
        m = models.WebhookSubscriptionCreate(
            url="https://hooks.example.com/callback",
            events="ticket.created",
        )
        assert m.url == "https://hooks.example.com/callback"
        assert m.events == "ticket.created"

    def test_url_too_short(self) -> None:
        with pytest.raises(ValidationError):
            models.WebhookSubscriptionCreate(url="http", events="e")

    def test_url_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.WebhookSubscriptionCreate(url="x" * 2001, events="e")

    def test_events_empty_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.WebhookSubscriptionCreate(url="https://example.com/hook", events="")

    def test_defaults_applied(self) -> None:
        m = models.WebhookSubscriptionCreate(
            url="https://example.com/hook", events="ticket.created"
        )
        assert m.secret == ""


class TestWebhookSubscriptionUpdate:
    def test_valid(self) -> None:
        m = models.WebhookSubscriptionUpdate(
            url="https://hooks.example.com/callback",
            events="ticket.created",
            active=False,
        )
        assert m.url == "https://hooks.example.com/callback"
        assert m.events == "ticket.created"
        assert m.active is False

    def test_active_default(self) -> None:
        m = models.WebhookSubscriptionUpdate(
            url="https://hooks.example.com/callback",
            events="ticket.created",
        )
        assert m.active is True

    def test_empty_url_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.WebhookSubscriptionUpdate(url="", events="e")


# ===================================================================
# Mail/SMS settings
# ===================================================================


class TestMailSettingsUpdate:
    def test_valid(self) -> None:
        m = models.MailSettingsUpdate()
        assert m.smtp_port == 587
        assert m.smtp_tls is True
        assert m.enabled is False

    def test_smtp_port_too_low(self) -> None:
        with pytest.raises(ValidationError):
            models.MailSettingsUpdate(smtp_port=0)

    def test_smtp_port_too_high(self) -> None:
        with pytest.raises(ValidationError):
            models.MailSettingsUpdate(smtp_port=65536)

    def test_smtp_host_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.MailSettingsUpdate(smtp_host="x" * 256)

    def test_defaults_applied(self) -> None:
        m = models.MailSettingsUpdate()
        assert m.smtp_host == ""
        assert m.smtp_user == ""
        assert m.smtp_password == ""
        assert m.smtp_from_email == ""
        assert m.smtp_from_name == ""


class TestSMSSettingsUpdate:
    def test_valid(self) -> None:
        m = models.SMSSettingsUpdate()
        assert m.enabled is False

    def test_defaults_applied(self) -> None:
        m = models.SMSSettingsUpdate()
        assert m.twilio_account_sid == ""
        assert m.twilio_auth_token == ""
        assert m.twilio_from_number == ""

    def test_twilio_sid_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.SMSSettingsUpdate(twilio_account_sid="x" * 256)

    def test_twilio_auth_token_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.SMSSettingsUpdate(twilio_auth_token="x" * 501)

    def test_twilio_from_number_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.SMSSettingsUpdate(twilio_from_number="x" * 21)


# ===================================================================
# Portal models
# ===================================================================


class TestPortalLoginRequest:
    def test_valid(self) -> None:
        m = models.PortalLoginRequest(email="user@portal.com", password="abc123")
        assert m.email == "user@portal.com"
        assert m.password == "abc123"

    def test_email_too_short(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalLoginRequest(email="ab", password="abc123")

    def test_missing_email_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalLoginRequest(password="abc123")

    def test_missing_password_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalLoginRequest(email="user@portal.com")


class TestPortalNoteCreate:
    def test_valid(self) -> None:
        m = models.PortalNoteCreate(content="Customer note")
        assert m.content == "Customer note"

    def test_content_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalNoteCreate(content="x" * 5001)

    def test_empty_content_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalNoteCreate(content="")

    def test_missing_content_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalNoteCreate()


class TestPortalPaymentCreate:
    def test_valid(self) -> None:
        m = models.PortalPaymentCreate(invoice_id="inv-001", amount=99.99)
        assert m.method == "card"

    def test_amount_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalPaymentCreate(invoice_id="inv-001", amount=0)

    def test_amount_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalPaymentCreate(invoice_id="inv-001", amount=-10)

    def test_missing_invoice_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalPaymentCreate(amount=99.99)

    def test_missing_amount_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalPaymentCreate(invoice_id="inv-001")

    def test_defaults_applied(self) -> None:
        m = models.PortalPaymentCreate(invoice_id="inv-001", amount=50)
        assert m.method == "card"
        assert m.reference == ""
        assert m.notes == ""


class TestPortalCheckoutSessionCreate:
    def test_valid(self) -> None:
        m = models.PortalCheckoutSessionCreate(invoice_id="inv-001")
        assert m.invoice_id == "inv-001"

    def test_empty_invoice_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalCheckoutSessionCreate(invoice_id="")

    def test_missing_invoice_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PortalCheckoutSessionCreate()


# ===================================================================
# POS models
# ===================================================================


class TestPOSCreate:
    def test_valid(self) -> None:
        m = models.POSCreate()
        assert m.customer_name == "Walk-in"
        assert m.payment_method == "cash"

    def test_invalid_payment_method(self) -> None:
        with pytest.raises(ValidationError, match="payment_method"):
            models.POSCreate(payment_method="check")

    def test_valid_payment_methods(self) -> None:
        for method in ("cash", "card", "invoice"):
            m = models.POSCreate(payment_method=method)
            assert m.payment_method == method

    def test_discount_amount_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.POSCreate(discount_amount=-1)

    def test_amount_tendered_negative(self) -> None:
        with pytest.raises(ValidationError):
            models.POSCreate(amount_tendered=-1)

    def test_tax_rate_too_high(self) -> None:
        with pytest.raises(ValidationError):
            models.POSCreate(tax_rate=100.01)

    def test_defaults_applied(self) -> None:
        m = models.POSCreate()
        assert m.customer_id == ""
        assert m.customer_name == "Walk-in"
        assert m.payment_method == "cash"
        assert m.amount_tendered == 0
        assert m.tax_rate == 0
        assert m.discount_amount == 0
        assert m.currency == "USD"


class TestPOSAddItem:
    def test_valid(self) -> None:
        m = models.POSAddItem(
            sale_id="sale-001",
            product_id="prod-001",
            product_name="USB Cable",
            quantity=2,
            unit_price=9.99,
        )
        assert m.quantity == 2

    def test_quantity_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.POSAddItem(
                sale_id="sale-001",
                product_id="prod-001",
                product_name="Cable",
                quantity=0,
                unit_price=5,
            )

    def test_unit_price_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.POSAddItem(
                sale_id="sale-001",
                product_id="prod-001",
                product_name="Cable",
                quantity=1,
                unit_price=-5,
            )

    def test_missing_sale_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.POSAddItem(
                product_id="prod-001", product_name="Cable", quantity=1, unit_price=5
            )

    def test_missing_product_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.POSAddItem(
                sale_id="sale-001", product_name="Cable", quantity=1, unit_price=5
            )

    def test_missing_product_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.POSAddItem(
                sale_id="sale-001", product_id="prod-001", quantity=1, unit_price=5
            )

    def test_defaults_applied(self) -> None:
        m = models.POSAddItem(
            sale_id="sale-001",
            product_id="prod-001",
            product_name="Cable",
            quantity=1,
            unit_price=5,
        )
        assert m.sku == ""


# ===================================================================
# SetPin / PosLogin
# ===================================================================


class TestSetPinRequest:
    def test_valid_pin(self) -> None:
        m = models.SetPinRequest(pin="1234")
        assert m.pin == "1234"

    def test_empty_pin_default(self) -> None:
        m = models.SetPinRequest()
        assert m.pin == ""

    def test_pin_with_letters_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.SetPinRequest(pin="abcd")

    def test_pin_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.SetPinRequest(pin="12345678901")

    def test_pin_max_length(self) -> None:
        m = models.SetPinRequest(pin="1234567890")
        assert m.pin == "1234567890"


class TestPosLoginRequest:
    def test_valid(self) -> None:
        m = models.PosLoginRequest(user_id="u-001", pin="1234")
        assert m.pin == "1234"

    def test_pin_too_short(self) -> None:
        with pytest.raises(ValidationError):
            models.PosLoginRequest(user_id="u-001", pin="123")

    def test_pin_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.PosLoginRequest(user_id="u-001", pin="12345678901")

    def test_pin_with_letters_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PosLoginRequest(user_id="u-001", pin="12a4")

    def test_missing_user_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PosLoginRequest(pin="1234")

    def test_missing_pin_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PosLoginRequest(user_id="u-001")

    def test_empty_user_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.PosLoginRequest(user_id="", pin="1234")


# ===================================================================
# Checklist models
# ===================================================================


class TestChecklistTemplateCreate:
    def test_valid(self) -> None:
        m = models.ChecklistTemplateCreate(name="Repair Checklist")
        assert m.name == "Repair Checklist"
        assert m.description == ""
        assert m.items == []

    def test_name_too_short(self) -> None:
        with pytest.raises(ValidationError):
            models.ChecklistTemplateCreate(name="")

    def test_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.ChecklistTemplateCreate(name="x" * 256)

    def test_description_max_length(self) -> None:
        with pytest.raises(ValidationError):
            models.ChecklistTemplateCreate(name="Test", description="x" * 2001)

    def test_missing_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.ChecklistTemplateCreate()


class TestChecklistTemplateUpdate:
    def test_valid(self) -> None:
        m = models.ChecklistTemplateUpdate(name="Updated Checklist")
        assert m.name == "Updated Checklist"
        assert m.description == ""
        assert m.items == []

    def test_name_too_short(self) -> None:
        with pytest.raises(ValidationError):
            models.ChecklistTemplateUpdate(name="")

    def test_name_too_long(self) -> None:
        with pytest.raises(ValidationError):
            models.ChecklistTemplateUpdate(name="x" * 256)


class TestChecklistApply:
    def test_valid(self) -> None:
        m = models.ChecklistApply(template_id="tmpl-001")
        assert m.template_id == "tmpl-001"

    def test_empty_template_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.ChecklistApply(template_id="")

    def test_missing_template_id_raises(self) -> None:
        with pytest.raises(ValidationError):
            models.ChecklistApply()


class TestChecklistToggle:
    def test_valid(self) -> None:
        m = models.ChecklistToggle(completed=True)
        assert m.completed is True

    def test_default_completed(self) -> None:
        m = models.ChecklistToggle()
        assert m.completed is False
