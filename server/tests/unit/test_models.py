"""Unit tests for the extracted model modules.

Verifies that each model module can be imported independently,
constructs valid instances, performs HTML sanitization, and
rejects invalid data.
"""

from __future__ import annotations

from datetime import datetime
import pytest
from pydantic import ValidationError

# Import all model classes from the package
from models import (
    LoginRequest, SetPasswordRequest,
    CustomerCreate, CustomerUpdate,
    TicketCreate, TicketTimerStart, TicketStatusUpdate, TicketAssign, TicketNoteCreate,
    InvoiceCreate, InvoiceStatusUpdate, InvoiceLineItemCreate, InvoiceTaxRateUpdate,
    BulkInvoiceStatusUpdate, BulkInvoiceEdit,
    PaymentCreate,
    AppointmentCreate, AppointmentStatusUpdate, AppointmentRecurrence, GenerateNextOccurrence,
    ProductCreate, ProductQuantityUpdate,
    PurchaseOrderCreate, PurchaseOrderStatusUpdate, POLineItemCreate, POReceiveItem, POApprovalAction,
    ScheduledReportCreate, ScheduledReportUpdate,
    EstimateCreate, EstimateStatusUpdate, EstimateLineItemCreate,
    TaxRateCreate, TaxRateUpdate,
    InventoryAdjustmentCreate, StockTransferRequest,
    TenantCreate, TenantUpdate, TenantMemberAdd, TenantMemberRoleUpdate,
    CustomFieldDefinitionCreate, CustomFieldValuesUpdate,
    ChecklistTemplateCreate, ChecklistTemplateUpdate, ChecklistApply, ChecklistToggle,
    WebhookSubscriptionCreate, WebhookSubscriptionUpdate,
    UserCreate, UserSettingsUpdate,
    MailSettingsUpdate, SMSSettingsUpdate,
    PortalLoginRequest, PortalNoteCreate, PortalPaymentCreate, PortalSetPassword,
    PortalCheckoutSessionCreate, ForgotPasswordRequest, ResetPasswordRequest,
    TenantMigrate,
    RecurringInvoiceLineItem, RecurringInvoiceRuleCreate, RecurringInvoiceRuleUpdate,
    SavePaymentMethodRequest, SetDefaultPaymentMethodRequest, PortalPayWithSavedCard,
    POSCreate, POSAddItem,
    Setup2FARequest, CompleteLoginRequest, Disable2FARequest, SetPinRequest, PosLoginRequest,
    DayHours, BusinessHoursUpdate,
)

# ── Test HTML sanitization ──────────────────────────────────────────────────


def test_sanitization_strips_html_from_string_fields():
    """SanitizedModel should strip HTML tags from string fields."""
    c = CustomerCreate(
        first_name="<b>John</b>",
        last_name="<script>alert('xss')</script>Doe",
        email="test@test.com",
    )
    assert c.first_name == "John"
    assert c.last_name == "alert('xss')Doe"


def test_sanitization_skips_password():
    """Password fields should NOT have HTML stripped."""
    user = SetPasswordRequest(password="<secret>")
    assert user.password == "<secret>"


# ── Auth models ─────────────────────────────────────────────────────────────


class TestAuthModels:
    def test_login_request_valid(self):
        r = LoginRequest(email="admin@test.com", password="secret")
        assert r.email == "admin@test.com"
        assert r.password == "secret"

    def test_login_request_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="", password="x")

    def test_login_request_invalid_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="a@b.com", password="")

    def test_set_password(self):
        r = SetPasswordRequest(password="newpass")
        assert r.password == "newpass"

    def test_set_password_too_short(self):
        with pytest.raises(ValidationError):
            SetPasswordRequest(password="")  # min_length=1


# ── Customer models ─────────────────────────────────────────────────────────


class TestCustomerModels:
    def test_create_minimal(self):
        c = CustomerCreate(first_name="Jane", last_name="Doe")
        assert c.first_name == "Jane"
        assert c.email == ""

    def test_create_full(self):
        c = CustomerCreate(
            first_name="Jane", last_name="Doe",
            email="j@d.com", phone="555", company="ACME",
        )
        assert c.email == "j@d.com"

    def test_create_missing_first_name(self):
        with pytest.raises(ValidationError):
            CustomerCreate(first_name="", last_name="Doe")

    def test_create_missing_last_name(self):
        with pytest.raises(ValidationError):
            CustomerCreate(first_name="Jane", last_name="")

    def test_update_minimal(self):
        c = CustomerUpdate(first_name="Jane", last_name="Doe")
        assert c.first_name == "Jane"

    def test_update_phone_strips_html(self):
        c = CustomerUpdate(first_name="A", last_name="B", phone="<em>555</em>")
        assert c.phone == "555"


# ── Ticket models ────────────────────────────────────────────────────────────


class TestTicketModels:
    def test_create_customer_onlymal(self):
        t = TicketCreate(customer_id="c1", title="Broken phone")
        assert t.title == "Broken phone"
        assert t.priority == "normal"

    def test_create_strips_html(self):
        t = TicketCreate(customer_id="c1", title="<b>Urgent</b>")
        assert t.title == "Urgent"

    def test_create_missing_customer(self):
        with pytest.raises(ValidationError):
            TicketCreate(customer_id="", title="Test")

    def test_timer_start(self):
        t = TicketTimerStart(user_id="u1")
        assert t.user_id == "u1"

    def test_status_update(self):
        s = TicketStatusUpdate(status="completed")
        assert s.status == "completed"

    def test_assign(self):
        a = TicketAssign(assigned_user_id="u2")
        assert a.assigned_user_id == "u2"

    def test_note_create(self):
        n = TicketNoteCreate(content="Fixed it")
        assert n.content == "Fixed it"
        assert n.internal is False

    def test_note_create_with_html(self):
        n = TicketNoteCreate(content="<p>Fixed</p>", author="<b>Tech</b>")
        assert n.content == "Fixed"
        assert n.author == "Tech"


# ── Invoice models ──────────────────────────────────────────────────────────


class TestInvoiceModels:
    def test_create_minimal(self):
        inv = InvoiceCreate(customer_id="c1")
        assert inv.customer_id == "c1"

    def test_create_minimal(self):
        inv = InvoiceCreate(customer_id="c1")
        assert inv.customer_id == "c1"

    def test_status_update(self):
        s = InvoiceStatusUpdate(status="paid")
        assert s.status == "paid"

    def test_line_item_create(self):
        li = InvoiceLineItemCreate(description="Part", quantity=2, unit_price=25.0)
        assert li.unit_price == 25.0


# ── Payment models ──────────────────────────────────────────────────────────


class TestPaymentModels:
    def test_create(self):
        p = PaymentCreate(invoice_id="inv1", customer_id="c1", amount=100.0, method="cash")
        assert p.amount == 100.0

    def test_html_stripped(self):
        p = PaymentCreate(invoice_id="inv1", customer_id="c1", amount=50.0, method="<script>cash</script>")
        assert p.method == "cash"


# ── POS models ──────────────────────────────────────────────────────────────


class TestPOSModels:
    def test_create_defaults(self):
        p = POSCreate()
        assert p.customer_name == "Walk-in"
        assert p.payment_method == "cash"
        assert p.currency == "USD"

    def test_create_custom(self):
        p = POSCreate(customer_id="c1", customer_name="Bob", payment_method="card")
        assert p.customer_name == "Bob"

    def test_add_item(self):
        i = POSAddItem(sale_id="s1", product_id="p1", product_name="Widget", quantity=2, unit_price=10.0)
        assert i.quantity == 2

    def test_add_item_negative_quantity(self):
        with pytest.raises(ValidationError):
            POSAddItem(sale_id="s1", product_id="p1", product_name="W", quantity=-1, unit_price=10.0)


# ── Tenant models ───────────────────────────────────────────────────────────


class TestTenantModels:
    def test_create(self):
        t = TenantCreate(name="ACME Repair", slug="acme")
        assert t.name == "ACME Repair"

    def test_create_strips_html(self):
        t = TenantCreate(name="<b>ACME</b>", slug="acme")
        assert t.name == "ACME"


# ── TwoFA models ────────────────────────────────────────────────────────────


class TestTwoFAModels:
    def test_setup(self):
        r = Setup2FARequest(code="123456")
        assert r.code == "123456"

    def test_complete_login(self):
        r = CompleteLoginRequest(temp_token="tok123", code="123456")
        assert r.temp_token == "tok123"
        assert r.code == "123456"

    def test_disable(self):
        r = Disable2FARequest(code="123456")
        assert r.code == "123456"


# ── Business Hours models ───────────────────────────────────────────────────


class TestBusinessHoursModels:
    def test_day_hours_defaults(self):
        d = DayHours()
        assert d.enabled is True
        assert d.open == "09:00"

    def test_business_hours_update(self):
        b = BusinessHoursUpdate()
        assert b.monday.enabled is True
        assert b.sunday.enabled is False


# ── Mail/SMS settings models ────────────────────────────────────────────────


class TestMailSmsSettings:
    def test_mail_update(self):
        m = MailSettingsUpdate(smtp_host="smtp.gmail.com", smtp_port=587)
        assert m.smtp_host == "smtp.gmail.com"

    def test_sms_update(self):
        s = SMSSettingsUpdate(twilio_from_number="+15551234567")
        assert s.twilio_from_number == "+15551234567"


# ── Checklist models ────────────────────────────────────────────────────────


class TestChecklistModels:
    def test_template_create(self):
        c = ChecklistTemplateCreate(name="New Device Setup")
        assert c.name == "New Device Setup"

    def test_template_update(self):
        c = ChecklistTemplateUpdate(name="Updated")
        assert c.name == "Updated"

    def test_apply(self):
        c = ChecklistApply(template_id="tmpl1")
        assert c.template_id == "tmpl1"

    def test_toggle(self):
        c = ChecklistToggle(completed=True)
        assert c.completed is True


# ── Recurring Invoice models ────────────────────────────────────────────────


class TestRecurringInvoiceModels:
    def test_line_item(self):
        li = RecurringInvoiceLineItem(description="Rent", quantity=1, unit_price=1000)
        assert li.unit_price == 1000

    def test_rule_create(self):
        r = RecurringInvoiceRuleCreate(
            customer_id="c1",
            name="Monthly Rent",
            line_items=[{"description": "Rent", "quantity": 1, "unit_price": 1000}],
            frequency="monthly",
            day_of_month=1,
        )
        assert r.frequency == "monthly"
        assert r.name == "Monthly Rent"

    def test_rule_update(self):
        r = RecurringInvoiceRuleUpdate(name="Rent", frequency="monthly", due_date_days=15)
        assert r.due_date_days == 15


# ── Tenant models ───────────────────────────────────────────────────────────


class TestPortalModels:
    def test_login_request(self):
        r = PortalLoginRequest(email="test@test.com", password="test")
        assert r.email == "test@test.com"

    def test_note_create(self):
        n = PortalNoteCreate(content="Hello")
        assert n.content == "Hello"

    def test_payment_create(self):
        p = PortalPaymentCreate(amount=50.0, invoice_id="inv1")
        assert p.amount == 50.0

    def test_set_password(self):
        p = PortalSetPassword(password="newpass")
        assert p.password == "newpass"


# ── Product models ──────────────────────────────────────────────────────────


class TestProductModels:
    def test_create(self):
        p = ProductCreate(name="Screen Protector")
        assert p.name == "Screen Protector"

    def test_create_with_html(self):
        p = ProductCreate(name="<b>Screen</b>")
        assert p.name == "Screen"

    def test_quantity_update(self):
        q = ProductQuantityUpdate(quantity_on_hand=10)
        assert q.quantity_on_hand == 10
