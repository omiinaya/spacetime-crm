"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel
from server.models.auth import LoginRequest, SetPasswordRequest
from server.models.customers import CustomerCreate, CustomerUpdate
from server.models.tickets import TicketCreate, TicketTimerStart, TicketStatusUpdate, TicketAssign, TicketNoteCreate
from server.models.invoices import InvoiceCreate, InvoiceStatusUpdate, InvoiceLineItemCreate, InvoiceTaxRateUpdate, BulkInvoiceStatusUpdate, BulkInvoiceEdit
from server.models.payments import PaymentCreate
from server.models.appointments import AppointmentCreate, AppointmentStatusUpdate, AppointmentRecurrence, GenerateNextOccurrence
from server.models.products import ProductCreate, ProductQuantityUpdate
from server.models.purchase_orders import PurchaseOrderCreate, PurchaseOrderStatusUpdate, POLineItemCreate, POReceiveItem, POApprovalAction
from server.models.scheduled_reports import ScheduledReportCreate, ScheduledReportUpdate
from server.models.estimates import EstimateCreate, EstimateStatusUpdate, EstimateLineItemCreate
from server.models.tax_rates import TaxRateCreate, TaxRateUpdate
from server.models.inventory import InventoryAdjustmentCreate, StockTransferRequest
from server.models.tenants import TenantCreate, TenantUpdate, TenantMemberAdd, TenantMemberRoleUpdate
from server.models.custom_fields import CustomFieldDefinitionCreate, CustomFieldValuesUpdate
from server.models.checklist import ChecklistTemplateCreate, ChecklistTemplateUpdate, ChecklistApply, ChecklistToggle
from server.models.webhook import WebhookSubscriptionCreate, WebhookSubscriptionUpdate
from server.models.user import UserCreate, UserUpdate, UserSettingsUpdate
from server.models.mail_sms_settings import MailSettingsUpdate, SMSSettingsUpdate
from server.models.portal import PortalLoginRequest, PortalNoteCreate, PortalPaymentCreate, PortalSetPassword, PortalCheckoutSessionCreate, ForgotPasswordRequest, ResetPasswordRequest, TenantMigrate
from server.models.recurring_invoices import RecurringInvoiceLineItem, RecurringInvoiceRuleCreate, RecurringInvoiceRuleUpdate
from server.models.payment_methods import SavePaymentMethodRequest, SetDefaultPaymentMethodRequest, PortalPayWithSavedCard
from server.models.pos__counter_sale import POSCreate, POSAddItem
from server.models.twofa import Setup2FARequest, CompleteLoginRequest, Disable2FARequest, SetPinRequest, PosLoginRequest
from server.models.business_hours import DayHours, BusinessHoursUpdate
