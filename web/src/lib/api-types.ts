// API Types, interfaces, and constants
const API_BASE = "/api";

// ── Pagination types ──

export interface PaginationParams {
  offset?: number;
  limit?: number;
}

export interface PaginatedResponse<T> {
  total: number;
  offset: number;
  limit: number;
  [key: string]: T[] | number;
}

function buildPaginationParams(offset?: number, limit?: number): string {
  if (offset === undefined && limit === undefined) return "";
  const p = new URLSearchParams();
  if (offset !== undefined) p.set("offset", String(offset));
  if (limit !== undefined) p.set("limit", String(limit));
  return "?" + p.toString();
}

function getApiToken(): string | null {
  try {
    return localStorage.getItem("crm_token");
  } catch {
    return null;
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getApiToken();
  const authHeader: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {};
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...authHeader, ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

export interface Customer {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  mobile: string;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  zip: string;
  company: string;
  notes: string;
  tags: string;
  created_at: number;
  updated_at: number;
}

export interface CustomerGeoLocation {
  id: string;
  name: string;
  company: string;
  email: string;
  phone: string;
  address: string;
  address_line1: string;
  city: string;
  state: string;
  zip: string;
  latitude: number | null;
  longitude: number | null;
  has_location: boolean;
}

export interface Ticket {
  id: string;
  customer_id: string;
  ticket_number: number;
  title: string;
  description: string;
  device_type: string;
  device_model: string;
  device_serial: string;
  device_imei: string;
  device_password: string;
  estimate_id: string;
  invoice_id: string;
  status: string;
  priority: string;
  assigned_user_id: string;
  notes: string;
  created_at: number;
  updated_at: number;
}

export interface TicketNote {
  id: string;
  ticket_id: string;
  author: string;
  content: string;
  internal: boolean;
  created_at: number;
}

export interface TicketTimer {
  id: string;
  ticket_id: string;
  user_id: string;
  start_time: number;
  end_time: number;
  total_seconds: number;
  running: boolean;
}

export interface TicketSlaBreach {
  id: string;
  ticket_number: number;
  title: string;
  priority: string;
  created_at: number;
  elapsed_hours: number;
  target_hours: number;
}

export interface Invoice {
  id: string;
  customer_id: string;
  ticket_id: string;
  invoice_number: number;
  status: string;
  subtotal: number;
  tax_rate: number;
  tax_amount: number;
  total: number;
  discount_amount: number;
  discount_percent: number;
  notes: string;
  terms: string;
  due_date: number;
  created_at: number;
  updated_at: number;
  currency: string;
}

export interface InvoiceLineItem {
  id: string;
  invoice_id: string;
  item_type: string;
  description: string;
  quantity: number;
  unit_price: number;
  total: number;
  sort_order: number;
}

export interface InvoiceSummary {
  by_status: Record<string, { count: number; total: number }>;
  total_count: number;
  total_revenue: number;
  total_outstanding: number;
  overdue_count: number;
  overdue_total: number;
}

export interface Payment {
  id: string;
  invoice_id: string;
  customer_id: string;
  amount: number;
  method: string;
  reference: string;
  notes: string;
  created_at: number;
  currency: string;
}

export interface Appointment {
  id: string;
  customer_id: string;
  ticket_id: string;
  title: string;
  description: string;
  start_time: number;
  end_time: number;
  all_day: boolean;
  status: string;
  color: string;
  series_id: string;
  recurrence_rule: string;
  created_at: number;
  updated_at: number;
}
export interface Product {
  id: string;
  name: string;
  sku: string;
  barcode: string;
  description: string;
  category: string;
  price: number;
  cost: number;
  quantity_on_hand: number;
  quantity_committed: number;
  quantity_available: number;
  min_stock: number;
  location: string;
  active: boolean;
  created_at: number;
}

export interface InventoryAdjustment {
  id: string;
  product_id: string;
  quantity_change: number;
  reason: string;
  reference_id: string;
  notes: string;
  user_id: string;
  created_at: number;
}

export interface Estimate {
  id: string;
  customer_id: string;
  ticket_id: string;
  invoice_id: string;
  estimate_number: number;
  status: string;
  subtotal: number;
  tax_rate: number;
  tax_amount: number;
  total: number;
  discount_amount: number;
  notes: string;
  expires_at: number;
  created_at: number;
  updated_at: number;
  currency: string;
}

export interface EstimateLineItem {
  id: string;
  estimate_id: string;
  item_type: string;
  description: string;
  quantity: number;
  unit_price: number;
  total: number;
  sort_order: number;
}

export interface PurchaseOrder {
  id: string;
  vendor_name: string;
  po_number: number;
  status: string;
  approved_by: string;
  approved_at: number;
  subtotal: number;
  tax_amount: number;
  shipping_cost: number;
  total: number;
  notes: string;
  created_at: number;
  line_items?: PurchaseOrderLineItem[];
  receipt_progress?: number;
  currency: string;
}

export interface PurchaseOrderLineItem {
  id: string;
  purchase_order_id: string;
  product_id: string;
  description: string;
  quantity: number;
  unit_price: number;
  total: number;
  received_quantity: number;
}

export interface User {
  id: string;
  name: string;
  pin: string;
  email: string;
  role: string;
  active: boolean;
  totp_secret: string;
  totp_enabled: boolean;
  created_at: number;
}

export interface DashboardStats {
  total_customers: number;
  total_tickets: number;
  open_tickets: number;
  revenue: number;
  pending_revenue: number;
  upcoming_appointments: number;
  my_tickets?: Ticket[];
  my_ticket_counts?: { all: number; urgent: number; high: number; medium: number; low: number };
  today_appointments?: Appointment[];
  overdue_invoices?: Invoice[];
  overdue_invoices_count?: number;
  overdue_invoices_total?: number;
  monthly_revenue: number;
  revenue_target: number;
  avg_resolution_hours: number;
}

export interface MailSettings {
  host: string;
  port: number;
  username: string;
  use_tls: boolean;
  sender_name: string;
  sender_email: string;
  password?: string;
}

export interface TaxRate {
  id: string;
  name: string;
  rate: number;
  is_default: boolean;
  created_at: number;
  updated_at: number;
}

export interface SmsSettings {
  account_sid: string;
  from_number: string;
  configured: boolean;
  auth_token?: string;
}

export interface DayHours {
  enabled: boolean;
  open: string;
  close: string;
}

export interface BusinessHours {
  monday: DayHours;
  tuesday: DayHours;
  wednesday: DayHours;
  thursday: DayHours;
  friday: DayHours;
  saturday: DayHours;
  sunday: DayHours;
}

export interface ReportsData {
  revenue_by_month: { month: string; revenue: number }[];
  ticket_by_status: { status: string; count: number }[];
  invoice_by_status: { status: string; count: number }[];
  appointments_by_month: { month: string; appointments: number }[];
  customers_by_month: { month: string; new_customers: number }[];
  totals: {
    total_revenue: number;
    total_tickets: number;
    open_tickets: number;
    total_sent: number;
    total_paid: number;
    outstanding_revenue: number;
    avg_resolution_hours: number;
    sla_breach_count: number;
    sla_breach_rate: number;
    overdue_invoice_count: number;
    overdue_invoice_rate: number;
  };
  tech_closed: { user_name: string; closed_count: number }[];
  top_customers: { customer_name: string; revenue: number }[];
}

export interface ScheduledReport {
  id: string;
  tenant_id: string;
  name: string;
  report_type: string;
  schedule_frequency: string;
  schedule_config_json: string;
  recipients_json: string;
  filters_json: string;
  next_run_at: number;
  last_run_at: number;
  last_error: string;
  enabled: boolean;
  created_at: number;
  updated_at: number;
}

export interface ChecklistItem {
  label: string;
  sort_order: number;
}

export interface ChecklistTemplate {
  id: string;
  name: string;
  description: string;
  items: string; // JSON string of items
  created_at: number;
  updated_at: number;
}

export interface TicketChecklistItem {
  id: string;
  ticket_id: string;
  template_id: string;
  template_name: string;
  label: string;
  sort_order: number;
  completed: boolean;
  completed_by: string;
  completed_at: number;
  created_at: number;
}

export interface WebhookSubscription {
  id: string;
  url: string;
  events: string;
  secret: string;
  active: boolean;
  created_at: number;
  updated_at: number;
}

export interface POSCounterSale {
  id: string;
  tenant_id: string;
  customer_id: string;
  customer_name: string;
  items_count: number;
  subtotal: number;
  tax_rate: number;
  tax_amount: number;
  discount_amount: number;
  total: number;
  payment_method: string;
  amount_tendered: number;
  change_due: number;
  currency: string;
  receipt_number: number;
  status: string;
  created_at: number;
  created_by: string;
  refunded_at: number;
}

export interface POSCounterSaleDetail extends POSCounterSale {
  line_items: POSCounterSaleLineItem[];
}

export interface POSCounterSaleLineItem {
  id: string;
  tenant_id: string;
  sale_id: string;
  product_id: string;
  product_name: string;
  sku: string;
  quantity: number;
  unit_price: number;
  total: number;
  sort_order: number;
}

export interface POSAddItemPayload {
  sale_id: string;
  product_id: string;
  product_name: string;
  sku?: string;
  quantity: number;
  unit_price: number;
}

export const WEBHOOK_EVENTS = [
  "customer.created",
  "customer.updated",
  "customer.deleted",
  "ticket.created",
  "ticket.updated",
  "ticket.status_changed",
  "invoice.created",
  "invoice.status_changed",
  "invoice.paid",
  "payment.created",
  "estimate.created",
  "estimate.approved",
  "appointment.created",
] as const;

// ── Entity interfaces ──

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  logo_url: string;
  settings: string;
  created_at: number;
  updated_at: number;
}

export interface TenantMember {
  id: string;
  tenant_id: string;
  username: string;
  role: string;
  created_at: number;
}

export interface RecurringInvoiceRule {
  id: string;
  tenant_id: string;
  customer_id: string;
  name: string;
  frequency: string;
  interval_count: number;
  next_generation_date: number;
  last_generated_date: number;
  due_date_days: number;
  line_items_json: string;
  status: string;
  currency: string;
  created_at: number;
  updated_at: number;
}

export interface SavedPaymentMethod {
  id: string;
  tenant_id: string;
  customer_id: string;
  stripe_payment_method_id: string;
  brand: string;
  last4: string;
  exp_month: number;
  exp_year: number;
  is_default: boolean;
  created_at: number;
  updated_at: number;
}

export interface CustomFieldDefinition {
  id: string;
  entity_type: string;
  label: string;
  field_type: string;
  options: string;
  sort_order: number;
  required: boolean;
  active: boolean;
  created_at: number;
  updated_at: number;
}

export interface CustomFieldValue {
  id: string;
  entity_id: string;
  field_id: string;
  value: string;
  created_at: number;
  updated_at: number;
}

export interface UserSettings {
  user_id: string;
  theme: string;
  default_ticket_status: string;
  created_at: number;
  updated_at: number;
}

export interface AuditLogEntry {
  id: string;
  tenant_id: string;
  user_id: string;
  user_name: string;
  action: string;
  entity: string;
  entity_id: string;
  details: string;
  created_at: number;
}

// ── API client ──

