"""Pydantic request/response models for SpacetimeCRM API.


All POST/PUT endpoints should use these models instead of raw `body: dict`.
This provides type validation, clear error messages (422), and API docs.
"""

from pydantic import BaseModel, Field

from sanitize import SanitizedModel

# Make BaseModel an alias for SanitizedModel so ALL existing models
# automatically get HTML stripping without individual changes.
BaseModel = SanitizedModel
from models.auth import LoginRequest, SetPasswordRequest
from models.customers import CustomerCreate, CustomerUpdate
from models.tickets import TicketCreate, TicketTimerStart, TicketStatusUpdate, TicketAssign, TicketNoteCreate
from models.invoices import InvoiceCreate, InvoiceStatusUpdate, InvoiceLineItemCreate, InvoiceTaxRateUpdate, BulkInvoiceStatusUpdate, BulkInvoiceEdit
from models.payments import PaymentCreate
from models.appointments import AppointmentCreate, AppointmentStatusUpdate, AppointmentRecurrence, GenerateNextOccurrence
from models.products import ProductCreate, ProductQuantityUpdate
from models.purchase_orders import PurchaseOrderCreate, PurchaseOrderStatusUpdate, POLineItemCreate, POReceiveItem, POApprovalAction
from models.scheduled_reports import ScheduledReportCreate, ScheduledReportUpdate
from models.estimates import EstimateCreate, EstimateStatusUpdate, EstimateLineItemCreate
from models.tax_rates import TaxRateCreate, TaxRateUpdate
from models.inventory import InventoryAdjustmentCreate, StockTransferRequest
from models.tenants import TenantCreate, TenantUpdate, TenantMemberAdd, TenantMemberRoleUpdate
from models.custom_fields import CustomFieldDefinitionCreate, CustomFieldValuesUpdate
from models.checklist import ChecklistTemplateCreate, ChecklistTemplateUpdate, ChecklistApply, ChecklistToggle
from models.webhook import WebhookSubscriptionCreate, WebhookSubscriptionUpdate
from models.user import UserCreate, UserUpdate, UserSettingsUpdate
from models.mail_sms_settings import MailSettingsUpdate, SMSSettingsUpdate
from models.portal import PortalLoginRequest, PortalNoteCreate, PortalPaymentCreate, PortalSetPassword, PortalCheckoutSessionCreate, ForgotPasswordRequest, ResetPasswordRequest, TenantMigrate
from models.recurring_invoices import RecurringInvoiceLineItem, RecurringInvoiceRuleCreate, RecurringInvoiceRuleUpdate
from models.payment_methods import SavePaymentMethodRequest, SetDefaultPaymentMethodRequest, PortalPayWithSavedCard
from models.pos_counter_sale import POSCreate, POSAddItem
from models.twofa import Setup2FARequest, CompleteLoginRequest, Disable2FARequest, SetPinRequest, PosLoginRequest
from models.business_hours import DayHours, BusinessHoursUpdate
