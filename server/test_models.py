"""
Tests for server/models.py.

Tests Pydantic request/response model validation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from server.models import (
    AppointmentCreate,
    CustomerCreate,
    CustomerUpdate,
    CustomFieldDefinitionCreate,
    InvoiceCreate,
    LoginRequest,
    MailSettingsUpdate,
    PaymentCreate,
    ProductCreate,
    PurchaseOrderCreate,
    SetPasswordRequest,
    SMSSettingsUpdate,
    TaxRateCreate,
    TicketCreate,
    UserCreate,
    UserUpdate,
)


class TestModels:
    """Test suite for models.py."""

    # ── Auth Models ──

    def test_login_request_valid(self):
        model = LoginRequest(email="a@b.com", password="secret")
        assert model.email == "a@b.com"

    def test_login_request_rejects_short_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="ab", password="secret")

    def test_login_request_rejects_empty_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="a@b.com", password="")

    def test_set_password_valid(self):
        model = SetPasswordRequest(password="abcd")
        assert model.password == "abcd"

    def test_set_password_rejects_short(self):
        with pytest.raises(ValidationError):
            SetPasswordRequest(password="abc")

    # ── Customer Models ──

    def test_customer_create_valid(self):
        model = CustomerCreate(first_name="John", last_name="Doe")
        assert model.first_name == "John"
        assert model.last_name == "Doe"
        assert model.email == ""

    def test_customer_create_rejects_empty_first_name(self):
        with pytest.raises(ValidationError):
            CustomerCreate(first_name="", last_name="Doe")

    def test_customer_update_valid(self):
        model = CustomerUpdate(first_name="Jane", last_name="Smith", email="j@test.com")
        assert model.email == "j@test.com"

    # ── Ticket Models ──

    def test_ticket_create_valid(self):
        model = TicketCreate(customer_id="c1", title="Fix printer")
        assert model.title == "Fix printer"
        assert model.priority == "normal"

    def test_ticket_create_rejects_empty_customer(self):
        with pytest.raises(ValidationError):
            TicketCreate(customer_id="", title="Fix")

    # ── Invoice Models ──

    def test_invoice_create_valid(self):
        model = InvoiceCreate(customer_id="c1")
        assert model.customer_id == "c1"
        assert model.currency == "USD"

    def test_invoice_create_rejects_negative_discount(self):
        with pytest.raises(ValidationError):
            InvoiceCreate(customer_id="c1", discount_amount=-1)

    # ── Payment Models ──

    def test_payment_create_valid(self):
        model = PaymentCreate(invoice_id="i1", customer_id="c1", amount=50.0)
        assert model.amount == 50.0
        assert model.method == "cash"

    def test_payment_create_rejects_zero_amount(self):
        with pytest.raises(ValidationError):
            PaymentCreate(invoice_id="i1", customer_id="c1", amount=0)

    def test_payment_create_rejects_negative_amount(self):
        with pytest.raises(ValidationError):
            PaymentCreate(invoice_id="i1", customer_id="c1", amount=-10)

    # ── Appointment Models ──

    def test_appointment_create_valid(self):
        model = AppointmentCreate(
            customer_id="c1",
            title="Repair Laptop",
            start_time=1700000000,
            end_time=1700003600,
        )
        assert model.title == "Repair Laptop"
        assert model.all_day is False

    def test_appointment_create_rejects_negative_time(self):
        with pytest.raises(ValidationError):
            AppointmentCreate(
                customer_id="c1",
                title="Test",
                start_time=-1,
                end_time=100,
            )

    # ── Product Models ──

    def test_product_create_valid(self):
        model = ProductCreate(name="Widget")
        assert model.name == "Widget"
        assert model.active is True

    def test_product_create_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="")

    # ── Purchase Order Models ──

    def test_purchase_order_create_valid(self):
        model = PurchaseOrderCreate(vendor_name="Acme Inc")
        assert model.vendor_name == "Acme Inc"

    def test_purchase_order_create_rejects_empty_vendor(self):
        with pytest.raises(ValidationError):
            PurchaseOrderCreate(vendor_name="")

    # ── User Models ──

    def test_user_create_valid(self):
        model = UserCreate(name="Bob", email="bob@test.com")
        assert model.role == "tech"

    def test_user_create_rejects_invalid_role(self):
        with pytest.raises(ValidationError):
            UserCreate(name="Bob", email="b@t.com", role="superadmin")

    def test_user_update_valid(self):
        model = UserUpdate(name="Bob", email="b@t.com", role="admin", active=True)
        assert model.role == "admin"

    # ── Tax Rate Models ──

    def test_tax_rate_create_valid(self):
        model = TaxRateCreate(name="Sales Tax", rate=8.5)
        assert model.rate == 8.5

    def test_tax_rate_create_rejects_negative_rate(self):
        with pytest.raises(ValidationError):
            TaxRateCreate(name="Bad", rate=-1)

    def test_tax_rate_create_rejects_rate_over_100(self):
        with pytest.raises(ValidationError):
            TaxRateCreate(name="Bad", rate=101)

    # ── Settings Models ──

    def test_mail_settings_defaults(self):
        model = MailSettingsUpdate()
        assert model.smtp_port == 587
        assert model.smtp_tls is True
        assert model.enabled is False

    def test_sms_settings_defaults(self):
        model = SMSSettingsUpdate()
        assert model.enabled is False

    # ── Custom Field Models ──

    def test_custom_field_definition_valid(self):
        model = CustomFieldDefinitionCreate(
            entity_type="customer",
            label="Member Since",
            field_type="text",
        )
        assert model.label == "Member Since"

    def test_custom_field_definition_rejects_invalid_entity(self):
        with pytest.raises(ValidationError):
            CustomFieldDefinitionCreate(
                entity_type="bad",
                label="X",
                field_type="text",
            )

    def test_custom_field_definition_rejects_invalid_type(self):
        with pytest.raises(ValidationError):
            CustomFieldDefinitionCreate(
                entity_type="customer",
                label="X",
                field_type="invalid",
            )
