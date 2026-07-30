"""Pydantic request/response models for SpacetimeCRM API.

All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.

Re-exports all model classes from domain-specific submodules.
Import with:  from models import CustomerCreate
"""

from .appointments import (
    AppointmentCreate,
    AppointmentRecurrence,
    AppointmentStatusUpdate,
    GenerateNextOccurrence,
)
from .auth import (
    CompleteLoginRequest,
    Disable2FARequest,
    ForgotPasswordRequest,
    LoginRequest,
    PosLoginRequest,
    ResetPasswordRequest,
    SetPasswordRequest,
    SetPinRequest,
    Setup2FARequest,
)
from .base import BaseModel
from .business_hours import BusinessHoursUpdate, DayHours
from .checklists import (
    ChecklistApply,
    ChecklistTemplateCreate,
    ChecklistTemplateUpdate,
    ChecklistToggle,
)
from .custom_fields import CustomFieldDefinitionCreate, CustomFieldValuesUpdate
from .customers import CustomerCreate, CustomerUpdate
from .estimates import (
    EstimateCreate,
    EstimateLineItemCreate,
    EstimateStatusUpdate,
)
from .invoices import (
    BulkInvoiceEdit,
    BulkInvoiceStatusUpdate,
    InvoiceCreate,
    InvoiceLineItemCreate,
    InvoiceStatusUpdate,
    InvoiceTaxRateUpdate,
    PaymentCreate,
)
from .payment_methods import (
    PortalPayWithSavedCard,
    SavePaymentMethodRequest,
    SetDefaultPaymentMethodRequest,
)
from .portal import (
    PortalCheckoutSessionCreate,
    PortalLoginRequest,
    PortalNoteCreate,
    PortalPaymentCreate,
    PortalSetPassword,
)
from .pos import POSAddItem, POSCreate
from .products import (
    InventoryAdjustmentCreate,
    ProductCreate,
    ProductQuantityUpdate,
    StockTransferRequest,
)
from .purchase_orders import (
    POApprovalAction,
    POLineItemCreate,
    POReceiveItem,
    PurchaseOrderCreate,
    PurchaseOrderStatusUpdate,
)
from .recurring_invoices import (
    RecurringInvoiceLineItem,
    RecurringInvoiceRuleCreate,
    RecurringInvoiceRuleUpdate,
)
from .reports import ScheduledReportCreate, ScheduledReportUpdate
from .taxes import TaxRateCreate, TaxRateUpdate
from .tenants import (
    TenantCreate,
    TenantMemberAdd,
    TenantMemberRoleUpdate,
    TenantMigrate,
    TenantUpdate,
)
from .tickets import (
    TicketAssign,
    TicketCreate,
    TicketNoteCreate,
    TicketStatusUpdate,
    TicketTimerStart,
)
from .users import UserCreate, UserSettingsUpdate, UserUpdate
from .webhooks import (
    MailSettingsUpdate,
    SMSSettingsUpdate,
    WebhookSubscriptionCreate,
    WebhookSubscriptionUpdate,
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
