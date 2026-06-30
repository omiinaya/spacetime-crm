"""Pydantic request/response models for SpacetimeCRM API.

All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel


# ─── Auth ────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class SetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=4, max_length=255)


# ─── Customers ───────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(default="", max_length=255)
    phone: str = Field(default="", max_length=50)
    mobile: str = Field(default="", max_length=50)
    company: str = Field(default="", max_length=255)
    address_line1: str = Field(default="", max_length=255)
    address_line2: str = Field(default="", max_length=255)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=50)
    zip: str = Field(default="", max_length=20)
    notes: str = Field(default="", max_length=2000)
    tags: str = Field(default="", max_length=500)


class CustomerUpdate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(default="", max_length=255)
    phone: str = Field(default="", max_length=50)
    mobile: str = Field(default="", max_length=50)
    company: str = Field(default="", max_length=255)
    address_line1: str = Field(default="", max_length=255)
    address_line2: str = Field(default="", max_length=255)
    city: str = Field(default="", max_length=100)
    state: str = Field(default="", max_length=50)
    zip: str = Field(default="", max_length=20)
    notes: str = Field(default="", max_length=2000)
    tags: str = Field(default="", max_length=500)


# ─── Tickets ─────────────────────────────────────────────────────

class TicketCreate(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=5000)
    device_type: str = Field(default="", max_length=100)
    device_model: str = Field(default="", max_length=100)
    device_serial: str = Field(default="", max_length=100)
    priority: str = Field(default="normal", max_length=50)


class TicketTimerStart(BaseModel):
    user_id: str = Field(default="", max_length=100)


class TicketStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)


class TicketAssign(BaseModel):
    assigned_user_id: str = Field(..., min_length=1, max_length=100)


class TicketNoteCreate(BaseModel):
    author: str = Field(default="", max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    internal: bool = False


# ─── Invoices ────────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=100)
    ticket_id: str = Field(default="", max_length=100)
    notes: str = Field(default="", max_length=2000)
    terms: str = Field(default="", max_length=500)
    due_date: int = Field(default=0, ge=0)


class InvoiceStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)


class InvoiceLineItemCreate(BaseModel):
    item_type: str = Field(default="service", max_length=100)
    description: str = Field(default="", max_length=500)
    quantity: float = Field(default=1, ge=0)
    unit_price: float = Field(default=0, ge=0)


class InvoiceTaxRateUpdate(BaseModel):
    tax_rate: float = Field(..., ge=0, le=100)


# ─── Payments ────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    invoice_id: str = Field(..., min_length=1, max_length=100)
    customer_id: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    method: str = Field(default="cash", max_length=50)
    reference: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=2000)


# ─── Appointments ────────────────────────────────────────────────

class AppointmentCreate(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=100)
    ticket_id: str = Field(default="", max_length=100)
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=2000)
    start_time: int = Field(..., ge=0)
    end_time: int = Field(..., ge=0)
    all_day: bool = False
    series_id: str = Field(default="", max_length=100)
    recurrence_rule: str = Field(default="", max_length=50)


class AppointmentStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)


class AppointmentRecurrence(BaseModel):
    recurrence_rule: str = Field(..., max_length=50)


class GenerateNextOccurrence(BaseModel):
    series_id: str = Field(..., min_length=1, max_length=100)


# ─── Products ────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(default="", max_length=100)
    barcode: str = Field(default="", max_length=100)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="", max_length=100)
    price: float = Field(default=0, ge=0)
    cost: float = Field(default=0, ge=0)
    quantity_on_hand: float = Field(default=0, ge=0)
    min_stock: float = Field(default=0, ge=0)
    location: str = Field(default="", max_length=255)
    active: bool = True


class ProductQuantityUpdate(BaseModel):
    quantity_on_hand: float = Field(..., ge=0)


# ─── Purchase Orders ─────────────────────────────────────────────

class PurchaseOrderCreate(BaseModel):
    vendor_name: str = Field(..., min_length=1, max_length=255)
    notes: str = Field(default="", max_length=2000)


class PurchaseOrderStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)


class POLineItemCreate(BaseModel):
    product_id: str = Field(default="")
    description: str = Field(default="", max_length=500)
    quantity: float = Field(default=1, ge=0)
    unit_price: float = Field(default=0, ge=0)


class POReceiveItem(BaseModel):
    received_quantity: float = Field(..., ge=0)
    items: list[dict] = []


# ─── Estimates ───────────────────────────────────────────────────

class EstimateCreate(BaseModel):
    customer_id: str = Field(..., min_length=1, max_length=100)
    ticket_id: str = Field(default="", max_length=100)
    notes: str = Field(default="", max_length=2000)
    expires_at: int = Field(default=0, ge=0)


class EstimateStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)


class EstimateLineItemCreate(BaseModel):
    item_type: str = Field(default="service", max_length=100)
    description: str = Field(default="", max_length=500)
    quantity: float = Field(default=1, ge=0)
    unit_price: float = Field(default=0, ge=0)


# ─── Tax Rates ───────────────────────────────────────────────────

class TaxRateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    rate: float = Field(..., ge=0, le=100)
    is_default: bool = False


class TaxRateUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    rate: float = Field(..., ge=0, le=100)
    is_default: bool = False


# ─── Inventory ───────────────────────────────────────────────────

class InventoryAdjustmentCreate(BaseModel):
    quantity_change: float = Field(...)
    reason: str = Field(default="other", max_length=100)
    reference_id: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=2000)
    user_id: str = Field(default="", max_length=100)


# ─── Tenants ─────────────────────────────────────────────────────

class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(default="", max_length=255)


class TenantUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(default="", max_length=255)
    logo_url: str = Field(default="", max_length=1000)
    settings: str = Field(default="{}", max_length=10000)


class TenantMemberAdd(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="user", max_length=50)


class TenantMemberRoleUpdate(BaseModel):
    role: str = Field(..., min_length=1, max_length=50)


# ─── Custom Fields ───────────────────────────────────────────────

class CustomFieldDefinitionCreate(BaseModel):
    id: str = Field(default="", max_length=100)
    entity_type: str = Field(..., pattern=r"^(customer|ticket|invoice|product)$")
    label: str = Field(..., min_length=1, max_length=255)
    field_type: str = Field(..., pattern=r"^(text|number|date|select|multiselect|checkbox|textarea)$")
    options: list[str] = Field(default=[])
    sort_order: int = Field(default=0, ge=0)
    required: bool = False
    active: bool = True


class CustomFieldValuesUpdate(BaseModel):
    values: dict[str, str | int | float | bool | list[str]] = {}


# ─── Checklist ───────────────────────────────────────────────────

class ChecklistTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    items: list[dict] = []


class ChecklistTemplateUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    items: list[dict] = []


class ChecklistApply(BaseModel):
    template_id: str = Field(..., min_length=1)


class ChecklistToggle(BaseModel):
    completed: bool = False


# ─── Webhook ─────────────────────────────────────────────────────

class WebhookSubscriptionCreate(BaseModel):
    url: str = Field(..., min_length=5, max_length=2000)
    events: str = Field(..., min_length=1)
    secret: str = Field(default="", max_length=500)


class WebhookSubscriptionUpdate(BaseModel):
    url: str = Field(..., min_length=5, max_length=2000)
    events: str = Field(..., min_length=1)
    secret: str = Field(default="", max_length=500)
    active: bool = True


# ─── User ────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=255)
    role: str = Field(default="tech", pattern=r"^(admin|tech|front_desk)$")


class UserUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=255)
    role: str = Field(..., pattern=r"^(admin|tech|front_desk)$")
    active: bool = True


# ─── Mail/SMS Settings ───────────────────────────────────────────

class MailSettingsUpdate(BaseModel):
    smtp_host: str = Field(default="", max_length=255)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str = Field(default="", max_length=255)
    smtp_password: str = Field(default="", max_length=500)
    smtp_from_email: str = Field(default="", max_length=255)
    smtp_from_name: str = Field(default="", max_length=100)
    smtp_tls: bool = True
    enabled: bool = False


class SMSSettingsUpdate(BaseModel):
    twilio_account_sid: str = Field(default="", max_length=255)
    twilio_auth_token: str = Field(default="", max_length=500)
    twilio_from_number: str = Field(default="", max_length=20)
    enabled: bool = False


# ─── Portal ──────────────────────────────────────────────────────

class PortalLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class PortalNoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class PortalPaymentCreate(BaseModel):
    invoice_id: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    method: str = Field(default="card", max_length=50)
    reference: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=2000)


class PortalSetPassword(BaseModel):
    password: str = Field(..., min_length=6, max_length=255)


class PortalCheckoutSessionCreate(BaseModel):
    invoice_id: str = Field(..., min_length=1)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)


class ResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=6, max_length=255)
    token: str = Field(..., min_length=1)


class TenantMigrate(BaseModel):
    name: str = Field(default="Default", max_length=255)
    slug: str = Field(default="", max_length=255)
