"""Tests for models module (Pydantic request/response models).

Covers validation, field constraints, and serialization for all entity types.
"""

import pytest
from pydantic import ValidationError

from models import (
    LoginRequest,
    SetPasswordRequest,
    CustomerCreate,
    CustomerUpdate,
    TicketCreate,
    TicketStatusUpdate,
    TicketAssign,
    TicketNoteCreate,
    TicketTimerStart,
    InvoiceCreate,
    InvoiceStatusUpdate,
    InvoiceLineItemCreate,
    BulkInvoiceStatusUpdate,
    PaymentCreate,
    AppointmentCreate,
    AppointmentStatusUpdate,
    ProductCreate,
    ProductQuantityUpdate,
    PurchaseOrderCreate,
    PurchaseOrderStatusUpdate,
    POLineItemCreate,
    EstimateCreate,
    EstimateStatusUpdate,
    EstimateLineItemCreate,
    TaxRateCreate,
    TaxRateUpdate,
    InventoryAdjustmentCreate,
    StockTransferRequest,
    TenantCreate,
    TenantUpdate,
    TenantMemberAdd,
    TenantMemberRoleUpdate,
    UserCreate,
    UserUpdate,
    UserSettingsUpdate,
    MailSettingsUpdate,
    SMSSettingsUpdate,
    CustomFieldDefinitionCreate,
    CustomFieldValuesUpdate,
    ChecklistTemplateCreate,
    ChecklistToggle,
    WebhookSubscriptionCreate,
    WebhookSubscriptionUpdate,
    ScheduledReportCreate,
    ScheduledReportUpdate,
    RecurringInvoiceRuleCreate,
    DayHours,
    BusinessHoursUpdate,
    SavePaymentMethodRequest,
    Setup2FARequest,
    PortalLoginRequest,
    POSCreate,
)


class TestAuthModels:
    def test_login_request_valid(self):
        r = LoginRequest(email="user@example.com", password="secret")
        assert r.email == "user@example.com"
        assert r.password == "secret"

    def test_login_request_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="ab", password="secret")

    def test_login_request_invalid_password(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="user@example.com", password="")

    def test_set_password_valid(self):
        r = SetPasswordRequest(password="newpass")
        assert r.password == "newpass"

    def test_set_password_too_short(self):
        with pytest.raises(ValidationError):
            SetPasswordRequest(password="ab")


class TestCustomerModels:
    def test_customer_create_valid(self):
        r = CustomerCreate(first_name="John", last_name="Doe")
        assert r.first_name == "John"
        assert r.last_name == "Doe"
        assert r.email == ""

    def test_customer_create_empty_name(self):
        with pytest.raises(ValidationError):
            CustomerCreate(first_name="", last_name="Doe")

    def test_customer_create_invalid_email_length(self):
        with pytest.raises(ValidationError):
            CustomerCreate(first_name="John", last_name="Doe", email="x" * 256)

    def test_customer_update_valid(self):
        r = CustomerUpdate(first_name="Jane", last_name="Smith", email="jane@example.com")
        assert r.email == "jane@example.com"

    def test_customer_update_with_all_fields(self):
        r = CustomerUpdate(
            first_name="Jane",
            last_name="Smith",
            email="j@ex.com",
            phone="555-1234",
            mobile="555-5678",
            company="Acme",
            address_line1="123 Main",
            city="NYC",
            state="NY",
            zip="10001",
            notes="VIP",
            tags="important",
        )
        assert r.company == "Acme"
        assert r.city == "NYC"
        assert r.notes == "VIP"


class TestTicketModels:
    def test_ticket_create_valid(self):
        r = TicketCreate(customer_id="cust_123", title="Broken phone")
        assert r.title == "Broken phone"
        assert r.priority == "normal"

    def test_ticket_create_missing_required(self):
        with pytest.raises(ValidationError):
            TicketCreate(customer_id="", title="Broken phone")

    def test_ticket_create_with_all_fields(self):
        r = TicketCreate(
            customer_id="c1",
            title="Fix PC",
            description="Blue screen",
            device_type="laptop",
            device_model="XPS 15",
            device_serial="SN123",
        )
        assert r.device_type == "laptop"
        assert r.device_model == "XPS 15"

    def test_ticket_status_update_valid(self):
        r = TicketStatusUpdate(status="in_progress")
        assert r.status == "in_progress"

    def test_ticket_assign_valid(self):
        r = TicketAssign(assigned_user_id="u_42")
        assert r.assigned_user_id == "u_42"

    def test_ticket_note_valid(self):
        r = TicketNoteCreate(content="Checked device")
        assert r.content == "Checked device"
        assert r.internal is False

    def test_ticket_note_with_author(self):
        r = TicketNoteCreate(content="Fixed it", author="Jane", internal=True)
        assert r.author == "Jane"
        assert r.internal is True

    def test_ticket_timer_start_with_user(self):
        r = TicketTimerStart(user_id="u_42")
        assert r.user_id == "u_42"


class TestInvoiceModels:
    def test_invoice_create_valid(self):
        r = InvoiceCreate(customer_id="c_1")
        assert r.customer_id == "c_1"
        assert r.currency == "USD"

    def test_invoice_create_with_all(self):
        r = InvoiceCreate(
            customer_id="c_1",
            ticket_id="t_1",
            notes="Thank you",
            terms="Net 30",
            due_date=1700000000000,
            discount_amount=10,
            discount_percent=5,
        )
        assert r.discount_amount == 10
        assert r.discount_percent == 5

    def test_invoice_status_update(self):
        r = InvoiceStatusUpdate(status="sent")
        assert r.status == "sent"

    def test_invoice_line_item_valid(self):
        r = InvoiceLineItemCreate(description="Labor", quantity=1, unit_price=100)
        assert r.unit_price == 100

    def test_bulk_invoice_status_update(self):
        r = BulkInvoiceStatusUpdate(invoice_ids=["i1", "i2"], status="paid")
        assert len(r.invoice_ids) == 2

    def test_bulk_invoice_empty_ids(self):
        with pytest.raises(ValidationError):
            BulkInvoiceStatusUpdate(invoice_ids=[], status="paid")


class TestPaymentModels:
    def test_payment_create_valid(self):
        r = PaymentCreate(invoice_id="i_1", customer_id="c_1", amount=50.0)
        assert r.amount == 50.0
        assert r.method == "cash"

    def test_payment_create_zero_amount(self):
        with pytest.raises(ValidationError):
            PaymentCreate(invoice_id="i_1", customer_id="c_1", amount=0)

    def test_payment_create_with_reference(self):
        r = PaymentCreate(invoice_id="i_1", customer_id="c_1", amount=99.99, reference="REF-001")
        assert r.reference == "REF-001"


class TestAppointmentModels:
    def test_appointment_create_valid(self):
        r = AppointmentCreate(
            customer_id="c_1", title="Screen Repair", start_time=1700000000000, end_time=1700003600000
        )
        assert r.title == "Screen Repair"

    def test_appointment_create_missing_title(self):
        with pytest.raises(ValidationError):
            AppointmentCreate(customer_id="c_1", title="", start_time=1, end_time=2)

    def test_appointment_status_update(self):
        r = AppointmentStatusUpdate(status="completed")
        assert r.status == "completed"


class TestProductModels:
    def test_product_create_valid(self):
        r = ProductCreate(name="USB Cable")
        assert r.name == "USB Cable"
        assert r.active is True
        assert r.price == 0

    def test_product_create_with_all(self):
        r = ProductCreate(name="HDMI Cable", sku="HDMI-6FT", price=12.99, quantity_on_hand=50, min_stock=5)
        assert r.sku == "HDMI-6FT"
        assert r.price == 12.99
        assert r.min_stock == 5

    def test_product_quantity_update(self):
        r = ProductQuantityUpdate(quantity_on_hand=100)
        assert r.quantity_on_hand == 100

    def test_product_negative_quantity(self):
        with pytest.raises(ValidationError):
            ProductQuantityUpdate(quantity_on_hand=-1)

    def test_product_create_empty_name(self):
        with pytest.raises(ValidationError):
            ProductCreate(name="")


class TestTaxRateModels:
    def test_tax_rate_create_valid(self):
        r = TaxRateCreate(name="Sales Tax", rate=8.25)
        assert r.rate == 8.25

    def test_tax_rate_too_high(self):
        with pytest.raises(ValidationError):
            TaxRateCreate(name="Too High", rate=101)

    def test_tax_rate_update(self):
        r = TaxRateUpdate(name="VAT", rate=20.0, is_default=True)
        assert r.is_default is True


class TestUserModels:
    def test_user_create_valid(self):
        r = UserCreate(name="Alice", email="alice@example.com")
        assert r.role == "tech"

    def test_user_create_admin(self):
        r = UserCreate(name="Admin", email="admin@ex.com", role="admin")
        assert r.role == "admin"

    def test_user_create_invalid_role(self):
        with pytest.raises(ValidationError):
            UserCreate(name="Bob", email="bob@ex.com", role="superadmin")

    def test_user_update(self):
        r = UserUpdate(name="Bob", email="bob@ex.com", role="front_desk", active=False)
        assert r.active is False

    def test_user_settings(self):
        r = UserSettingsUpdate(theme="dark")
        assert r.theme == "dark"

    def test_user_settings_invalid_theme(self):
        with pytest.raises(ValidationError):
            UserSettingsUpdate(theme="blue")


class TestMailSMSModels:
    def test_mail_settings_valid(self):
        r = MailSettingsUpdate(smtp_host="smtp.example.com", smtp_port=587)
        assert r.smtp_host == "smtp.example.com"
        assert r.enabled is False

    def test_mail_settings_invalid_port(self):
        with pytest.raises(ValidationError):
            MailSettingsUpdate(smtp_port=0)

    def test_sms_settings_valid(self):
        r = SMSSettingsUpdate(twilio_account_sid="ACxxx")
        assert r.twilio_account_sid == "ACxxx"


class TestTenantModels:
    def test_tenant_create_valid(self):
        r = TenantCreate(name="Shop One", slug="shop-one")
        assert r.name == "Shop One"

    def test_tenant_create_empty_name(self):
        with pytest.raises(ValidationError):
            TenantCreate(name="", slug="shop-one")

    def test_tenant_update(self):
        r = TenantUpdate(
            name="Shop One Updated", slug="shop-one", logo_url="https://example.com/logo.png", settings="{}"
        )
        assert r.logo_url == "https://example.com/logo.png"

    def test_tenant_member_add(self):
        r = TenantMemberAdd(username="jdoe")
        assert r.role == "user"

    def test_tenant_member_role_update(self):
        r = TenantMemberRoleUpdate(role="admin")
        assert r.role == "admin"


class TestCustomFieldModels:
    def test_custom_field_create_valid(self):
        r = CustomFieldDefinitionCreate(entity_type="customer", label="SSN", field_type="text")
        assert r.label == "SSN"

    def test_custom_field_invalid_entity_type(self):
        with pytest.raises(ValidationError):
            CustomFieldDefinitionCreate(entity_type="order", label="X", field_type="text")

    def test_custom_field_valid_entity_types(self):
        for etype in ("customer", "ticket", "invoice", "product"):
            r = CustomFieldDefinitionCreate(entity_type=etype, label="X", field_type="text")
            assert r.entity_type == etype

    def test_custom_field_values(self):
        r = CustomFieldValuesUpdate(values={"color": "red", "count": 3})
        assert r.values["color"] == "red"


class TestChecklistModels:
    def test_checklist_template_create(self):
        r = ChecklistTemplateCreate(name="Repair Checklist")
        assert r.name == "Repair Checklist"

    def test_checklist_template_toggle(self):
        r = ChecklistToggle(completed=True)
        assert r.completed is True


class TestWebhookModels:
    def test_webhook_create_valid(self):
        r = WebhookSubscriptionCreate(url="https://example.com/hook", events="ticket.created")
        assert r.url == "https://example.com/hook"

    def test_webhook_create_invalid_url(self):
        with pytest.raises(ValidationError):
            WebhookSubscriptionCreate(url="abc", events="test")

    def test_webhook_update(self):
        r = WebhookSubscriptionUpdate(url="https://ex.com/hook", events="*", secret="s3kr3t", active=True)
        assert r.active is True


class TestScheduleModels:
    def test_scheduled_report_create(self):
        r = ScheduledReportCreate(
            name="Weekly Report",
            report_type="revenue",
            schedule_frequency="weekly",
            recipients=["admin@ex.com"],
        )
        assert r.name == "Weekly Report"

    def test_scheduled_report_invalid_type(self):
        # report_type/schedule_frequency are now validated at the route level
        # (400 business errors), not enforced as hard Pydantic patterns, so
        # the model accepts freeform values.
        r = ScheduledReportCreate(
            name="Bad",
            report_type="invalid",
            schedule_frequency="weekly",
            recipients=["a@b.com"],
        )
        assert r.report_type == "invalid"

    def test_scheduled_report_update(self):
        r = ScheduledReportUpdate(
            name="Monthly",
            report_type="tickets",
            schedule_frequency="monthly",
            recipients=["a@b.com"],
            enabled=False,
        )
        assert r.enabled is False


class TestPurchaseOrderModels:
    def test_po_create(self):
        r = PurchaseOrderCreate(vendor_name="Acme Supply")
        assert r.vendor_name == "Acme Supply"

    def test_po_status_update(self):
        r = PurchaseOrderStatusUpdate(status="received")
        assert r.status == "received"

    def test_po_line_item(self):
        r = POLineItemCreate(description="Widgets", quantity=10, unit_price=5.0)
        assert r.quantity == 10

    def test_po_create_empty_vendor(self):
        with pytest.raises(ValidationError):
            PurchaseOrderCreate(vendor_name="")


class TestEstimateModels:
    def test_estimate_create(self):
        r = EstimateCreate(customer_id="c_1")
        assert r.customer_id == "c_1"

    def test_estimate_status_update(self):
        r = EstimateStatusUpdate(status="approved")
        assert r.status == "approved"

    def test_estimate_line_item(self):
        r = EstimateLineItemCreate(description="Consulting", unit_price=150)
        assert r.unit_price == 150


class TestInventoryModels:
    def test_inventory_adjustment(self):
        r = InventoryAdjustmentCreate(quantity_change=-5)
        assert r.quantity_change == -5

    def test_stock_transfer(self):
        r = StockTransferRequest(source_product_id="p1", destination_product_id="p2", quantity=10)
        assert r.quantity == 10


class TestDayHours:
    def test_default_day_hours(self):
        r = DayHours()
        assert r.enabled is True
        assert r.open == "09:00"
        assert r.close == "18:00"

    def test_day_hours_invalid_time_format(self):
        with pytest.raises(ValidationError):
            DayHours(open="9:00")

    def test_business_hours_update(self):
        r = BusinessHoursUpdate()
        assert r.monday.enabled is True
        assert r.saturday.enabled is False

    def test_recurring_invoice_create(self):
        r = RecurringInvoiceRuleCreate(
            customer_id="c_1",
            name="Monthly Service",
            frequency="monthly",
        )
        assert r.name == "Monthly Service"

    def test_recurring_invoice_invalid_frequency(self):
        with pytest.raises(ValidationError):
            RecurringInvoiceRuleCreate(
                customer_id="c_1",
                name="Bad",
                frequency="yearly_ish",
            )

    def test_save_payment_method(self):
        r = SavePaymentMethodRequest(
            customer_id="c_1",
            stripe_payment_method_id="pm_123",
            brand="Visa",
            last4="4242",
            exp_month=12,
            exp_year=2028,
        )
        assert r.brand == "Visa"

    def test_2fa_setup(self):
        r = Setup2FARequest(code="123456")
        assert r.code == "123456"

    def test_2fa_invalid_code_length(self):
        with pytest.raises(ValidationError):
            Setup2FARequest(code="12345")

    def test_portal_login(self):
        r = PortalLoginRequest(email="user@ex.com", password="pass")
        assert r.email == "user@ex.com"

    def test_pos_create(self):
        r = POSCreate()
        assert r.customer_name == "Walk-in"
        assert r.payment_method == "cash"
