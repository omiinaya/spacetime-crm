"""Pydantic request/response models for SpacetimeCRM API.

All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.

Re-exports all model classes from domain-specific submodules.
Import with:  from models import CustomerCreate
"""

from .base import BaseModel

from .auth import (
    LoginRequest,
    SetPasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    Setup2FARequest,
    CompleteLoginRequest,
    Disable2FARequest,
    SetPinRequest,
    PosLoginRequest,
)

from .customers import CustomerCreate, CustomerUpdate

from .tickets import (
    TicketCreate,
    TicketTimerStart,
    TicketStatusUpdate,
    TicketAssign,
    TicketNoteCreate,
)

from .invoices import (
    InvoiceCreate,
    InvoiceStatusUpdate,
    InvoiceLineItemCreate,
    InvoiceTaxRateUpdate,
    BulkInvoiceStatusUpdate,
    BulkInvoiceEdit,
    PaymentCreate,
)

from .appointments import (
    AppointmentCreate,
    AppointmentStatusUpdate,
    AppointmentRecurrence,
    GenerateNextOccurrence,
)

from .products import (
    ProductCreate,
    ProductQuantityUpdate,
    InventoryAdjustmentCreate,
    StockTransferRequest,
)

from .purchase_orders import (
    PurchaseOrderCreate,
    PurchaseOrderStatusUpdate,
    POLineItemCreate,
    POReceiveItem,
    POApprovalAction,
)

from .reports import ScheduledReportCreate, ScheduledReportUpdate

from .estimates import (
    EstimateCreate,
    EstimateStatusUpdate,
    EstimateLineItemCreate,
)

from .taxes import TaxRateCreate, TaxRateUpdate

from .tenants import (
    TenantCreate,
    TenantUpdate,
    TenantMemberAdd,
    TenantMemberRoleUpdate,
    TenantMigrate,
)

from .webhooks import (
    WebhookSubscriptionCreate,
    WebhookSubscriptionUpdate,
    MailSettingsUpdate,
    SMSSettingsUpdate,
)

from .portal import (
    PortalLoginRequest,
    PortalNoteCreate,
    PortalPaymentCreate,
    PortalSetPassword,
    PortalCheckoutSessionCreate,
)

from .pos import POSCreate, POSAddItem

from .business_hours import DayHours, BusinessHoursUpdate

from .custom_fields import CustomFieldDefinitionCreate, CustomFieldValuesUpdate

from .checklists import (
    ChecklistTemplateCreate,
    ChecklistTemplateUpdate,
    ChecklistApply,
    ChecklistToggle,
)

from .users import UserCreate, UserUpdate, UserSettingsUpdate

from .recurring_invoices import (
    RecurringInvoiceLineItem,
    RecurringInvoiceRuleCreate,
    RecurringInvoiceRuleUpdate,
)

from .payment_methods import (
    SavePaymentMethodRequest,
    SetDefaultPaymentMethodRequest,
    PortalPayWithSavedCard,
)

# Explicitly list __all__ for wildcard imports
__all__ = [
    # base
    "BaseModel",
    # auth
    "LoginRequest",
    "SetPasswordRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "Setup2FARequest",
    "CompleteLoginRequest",
    "Disable2FARequest",
    "SetPinRequest",
    "PosLoginRequest",
    # customers
    "CustomerCreate",
    "CustomerUpdate",
    # tickets
    "TicketCreate",
    "TicketTimerStart",
    "TicketStatusUpdate",
    "TicketAssign",
    "TicketNoteCreate",
    # invoices
    "InvoiceCreate",
    "InvoiceStatusUpdate",
    "InvoiceLineItemCreate",
    "InvoiceTaxRateUpdate",
    "BulkInvoiceStatusUpdate",
    "BulkInvoiceEdit",
    "PaymentCreate",
    # appointments
    "AppointmentCreate",
    "AppointmentStatusUpdate",
    "AppointmentRecurrence",
    "GenerateNextOccurrence",
    # products
    "ProductCreate",
    "ProductQuantityUpdate",
    "InventoryAdjustmentCreate",
    "StockTransferRequest",
    # purchase orders
    "PurchaseOrderCreate",
    "PurchaseOrderStatusUpdate",
    "POLineItemCreate",
    "POReceiveItem",
    "POApprovalAction",
    # reports
    "ScheduledReportCreate",
    "ScheduledReportUpdate",
    # estimates
    "EstimateCreate",
    "EstimateStatusUpdate",
    "EstimateLineItemCreate",
    # taxes
    "TaxRateCreate",
    "TaxRateUpdate",
    # tenants
    "TenantCreate",
    "TenantUpdate",
    "TenantMemberAdd",
    "TenantMemberRoleUpdate",
    "TenantMigrate",
    # webhooks
    "WebhookSubscriptionCreate",
    "WebhookSubscriptionUpdate",
    "MailSettingsUpdate",
    "SMSSettingsUpdate",
    # portal
    "PortalLoginRequest",
    "PortalNoteCreate",
    "PortalPaymentCreate",
    "PortalSetPassword",
    "PortalCheckoutSessionCreate",
    # POS
    "POSCreate",
    "POSAddItem",
    # business hours
    "DayHours",
    "BusinessHoursUpdate",
    # custom fields
    "CustomFieldDefinitionCreate",
    "CustomFieldValuesUpdate",
    # checklists
    "ChecklistTemplateCreate",
    "ChecklistTemplateUpdate",
    "ChecklistApply",
    "ChecklistToggle",
    # users
    "UserCreate",
    "UserUpdate",
    "UserSettingsUpdate",
    # recurring invoices
    "RecurringInvoiceLineItem",
    "RecurringInvoiceRuleCreate",
    "RecurringInvoiceRuleUpdate",
    # payment methods
    "SavePaymentMethodRequest",
    "SetDefaultPaymentMethodRequest",
    "PortalPayWithSavedCard",
]
