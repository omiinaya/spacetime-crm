export * from './api-types';

import type {
  DashboardStats,
  Customer,
  CustomerGeoLocation,
  Ticket,
  TicketNote,
  TicketTimer,
  TicketSlaBreach,
  Invoice,
  InvoiceLineItem,
  InvoiceSummary,
  Payment,
  Appointment,
  Product,
  InventoryAdjustment,
  Estimate,
  EstimateLineItem,
  PurchaseOrder,
  PurchaseOrderLineItem,
  User,
  MailSettings,
  TaxRate,
  SmsSettings,
  BusinessHours,
  DayHours,
  ReportsData,
  ScheduledReport,
  ChecklistItem,
  ChecklistTemplate,
  TicketChecklistItem,
  WebhookSubscription,
  POSCounterSale,
  POSCounterSaleDetail,
  POSCounterSaleLineItem,
  POSAddItemPayload,
  Tenant,
  TenantMember,
  RecurringInvoiceRule,
  SavedPaymentMethod,
  CustomFieldDefinition,
  CustomFieldValue,
  UserSettings,
  AuditLogEntry,
} from './api-types';

const API_BASE = '/api';

function buildPaginationParams(offset?: number, limit?: number): string {
  if (offset === undefined && limit === undefined) return '';
  const p = new URLSearchParams();
  if (offset !== undefined) p.set('offset', String(offset));
  if (limit !== undefined) p.set('limit', String(limit));
  return '?' + p.toString();
}

function getApiToken(): string | null {
  try {
    return localStorage.getItem('crm_token');
  } catch {
    return null;
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getApiToken();
  const authHeader: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...authHeader,
      ...options?.headers,
    },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => 'Unknown error');
    throw new Error(`API ${res.status}: ${text.slice(0, 200)}`);
  }
  return res.json();
}

// ── API client object ──

export const api = {
  stats: {
    get: () => apiFetch<DashboardStats>('/stats'),
  },
  customers: {
    list: (search?: string, offset?: number, limit?: number) => {
      const p = new URLSearchParams();
      if (search) p.set('search', search);
      if (offset !== undefined) p.set('offset', String(offset));
      if (limit !== undefined) p.set('limit', String(limit));
      const qs = p.toString();
      return apiFetch<{
        customers: Customer[];
        total: number;
        offset: number;
        limit: number;
      }>(`/customers${qs ? `?${qs}` : ''}`);
    },
    create: (data: Partial<Customer>) =>
      apiFetch<{ ok: boolean }>('/customers', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<Customer>) =>
      apiFetch<{ ok: boolean }>(`/customers/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    delete: (id: string) => apiFetch<{ ok: boolean }>(`/customers/${id}`, { method: 'DELETE' }),
    geolocations: {
      list: () => apiFetch<{ locations: CustomerGeoLocation[] }>('/customers/geolocations'),
      geocode: (customerId: string) =>
        apiFetch<{
          ok: boolean;
          latitude?: number;
          longitude?: number;
          display_name?: string;
          error?: string;
        }>(`/customers/${customerId}/geocode`, { method: 'POST' }),
      geocodeAll: () =>
        apiFetch<{ geocoded: number; results: any[] }>('/customers/geocode-all', {
          method: 'POST',
        }),
    },
    setPortalPassword: (id: string, password: string) =>
      apiFetch<{ ok: boolean }>(`/customers/${id}/portal-password`, {
        method: 'POST',
        body: JSON.stringify({ password }),
      }),
    duplicates: () =>
      apiFetch<{
        duplicates: { field: string; value: string; customers: Customer[] }[];
        count: number;
      }>('/customers/duplicates'),
  },
  checklist: {
    templates: {
      list: (offset?: number, limit?: number) => {
        const p = new URLSearchParams();
        if (offset !== undefined) p.set('offset', String(offset));
        if (limit !== undefined) p.set('limit', String(limit));
        const qs = p.toString();
        return apiFetch<{
          templates: ChecklistTemplate[];
          total: number;
          offset: number;
          limit: number;
        }>(`/checklist-templates${qs ? `?${qs}` : ''}`);
      },
      create: (data: { name: string; description?: string; items?: any[] }) =>
        apiFetch<{ ok: boolean }>('/checklist-templates', {
          method: 'POST',
          body: JSON.stringify(data),
        }),
      update: (id: string, data: { name: string; description?: string; items?: any[] }) =>
        apiFetch<{ ok: boolean }>(`/checklist-templates/${id}`, {
          method: 'PUT',
          body: JSON.stringify(data),
        }),
      delete: (id: string) =>
        apiFetch<{ ok: boolean }>(`/checklist-templates/${id}`, {
          method: 'DELETE',
        }),
    },
    ticket: {
      list: (ticketId: string) =>
        apiFetch<{ items: TicketChecklistItem[] }>(`/tickets/${ticketId}/checklist`),
      apply: (ticketId: string, templateId: string) =>
        apiFetch<{ ok: boolean }>(`/tickets/${ticketId}/checklist/apply`, {
          method: 'POST',
          body: JSON.stringify({ template_id: templateId }),
        }),
      toggle: (ticketId: string, itemId: string, completed: boolean) =>
        apiFetch<{ ok: boolean }>(`/tickets/${ticketId}/checklist/${itemId}`, {
          method: 'PUT',
          body: JSON.stringify({ completed }),
        }),
      clear: (ticketId: string) =>
        apiFetch<{ ok: boolean }>(`/tickets/${ticketId}/checklist`, {
          method: 'DELETE',
        }),
    },
  },
  tickets: {
    list: (status?: string, customerId?: string, offset?: number, limit?: number) => {
      const p = new URLSearchParams();
      if (status) p.set('status', status);
      if (customerId) p.set('customer_id', customerId);
      if (offset !== undefined) p.set('offset', String(offset));
      if (limit !== undefined) p.set('limit', String(limit));
      const qs = p.toString();
      return apiFetch<{
        tickets: Ticket[];
        total: number;
        offset: number;
        limit: number;
      }>(`/tickets${qs ? `?${qs}` : ''}`);
    },
    create: (data: Partial<Ticket>) =>
      apiFetch<{ ok: boolean }>('/tickets', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    updateStatus: (id: string, status: string) =>
      apiFetch<{ ok: boolean }>(`/tickets/${id}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status }),
      }),
    assign: (id: string, assigned_user_id: string) =>
      apiFetch<{ ok: boolean }>(`/tickets/${id}/assign`, {
        method: 'PUT',
        body: JSON.stringify({ assigned_user_id }),
      }),
    notes: {
      list: (ticketId: string) => apiFetch<{ notes: TicketNote[] }>(`/tickets/${ticketId}/notes`),
      create: (ticketId: string, data: Partial<TicketNote>) =>
        apiFetch<{ ok: boolean }>(`/tickets/${ticketId}/notes`, {
          method: 'POST',
          body: JSON.stringify(data),
        }),
    },
    delete: (id: string) => apiFetch<{ ok: boolean }>(`/tickets/${id}`, { method: 'DELETE' }),
    sla: {
      breaches: () =>
        apiFetch<{ breaches: TicketSlaBreach[]; count: number }>('/tickets/sla-breached'),
      targets: () => apiFetch<{ targets: Record<string, number> }>('/tickets/sla-targets'),
      settings: () =>
        apiFetch<{ targets: Record<string, number>; updated_at: number }>('/tickets/sla-settings'),
      save: (targets: Record<string, number>) =>
        apiFetch<{ targets: Record<string, number>; ok: boolean }>('/tickets/sla-settings', {
          method: 'POST',
          body: JSON.stringify({ targets }),
        }),
    },
    timers: {
      list: (ticketId: string) =>
        apiFetch<{ timers: TicketTimer[] }>(`/tickets/${ticketId}/timers`),
      start: (ticketId: string, userId: string) =>
        apiFetch<{ ok: boolean }>(`/tickets/${ticketId}/timers/start`, {
          method: 'POST',
          body: JSON.stringify({ user_id: userId }),
        }),
      stop: (timerId: string) =>
        apiFetch<{ ok: boolean }>(`/timers/${timerId}/stop`, {
          method: 'POST',
        }),
      delete: (timerId: string) =>
        apiFetch<{ ok: boolean }>(`/timers/${timerId}`, { method: 'DELETE' }),
    },
  },
  invoices: {
    list: (status?: string, customerId?: string, offset?: number, limit?: number) => {
      const p = new URLSearchParams();
      if (status) p.set('status', status);
      if (customerId) p.set('customer_id', customerId);
      if (offset !== undefined) p.set('offset', String(offset));
      if (limit !== undefined) p.set('limit', String(limit));
      const qs = p.toString();
      return apiFetch<{
        invoices: Invoice[];
        total: number;
        offset: number;
        limit: number;
      }>(`/invoices${qs ? `?${qs}` : ''}`);
    },
    create: (data: Partial<Invoice>) =>
      apiFetch<{ ok: boolean }>('/invoices', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    updateStatus: (id: string, status: string) =>
      apiFetch<{ ok: boolean }>(`/invoices/${id}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status }),
      }),
    lineItems: {
      list: (invoiceId: string) =>
        apiFetch<{ line_items: InvoiceLineItem[] }>(`/invoices/${invoiceId}/line-items`),
      create: (invoiceId: string, data: Partial<InvoiceLineItem>) =>
        apiFetch<{ ok: boolean }>(`/invoices/${invoiceId}/line-items`, {
          method: 'POST',
          body: JSON.stringify(data),
        }),
      delete: (invoiceId: string, itemId: string) =>
        apiFetch<{ ok: boolean }>(`/invoices/${invoiceId}/line-items/${itemId}`, {
          method: 'DELETE',
        }),
    },
    delete: (id: string) => apiFetch<{ ok: boolean }>(`/invoices/${id}`, { method: 'DELETE' }),
    overdueCount: () => apiFetch<{ count: number; total: number }>('/invoices/overdue-count'),
    triggerOverdueCheck: () =>
      apiFetch<{ ok: boolean }>('/invoices/trigger-overdue-check', {
        method: 'POST',
      }),
    summary: () => apiFetch<InvoiceSummary>('/invoices/summary'),
    bulkStatusUpdate: (invoiceIds: string[], status: string) =>
      apiFetch<{ ok: boolean; updated: number; errors: number }>('/invoices/bulk-status-update', {
        method: 'POST',
        body: JSON.stringify({ invoice_ids: invoiceIds, status }),
      }),
    sendOverdueReminders: () =>
      apiFetch<{ ok: boolean; email: number; sms: number; total: number }>(
        '/invoices/send-overdue-reminders',
        { method: 'POST' },
      ),
    sendEmail: (invoiceId: string) =>
      apiFetch<{ ok: boolean; sent_to: string; invoice_number: number }>('/invoices/send-email', {
        method: 'POST',
        body: JSON.stringify({ invoice_id: invoiceId }),
      }),
    sendBatchEmail: (invoiceIds: string[]) =>
      apiFetch<{
        ok: boolean;
        sent: number;
        failed: number;
        skipped: number;
        details: any[];
      }>('/invoices/send-batch-email', {
        method: 'POST',
        body: JSON.stringify({ invoice_ids: invoiceIds }),
      }),
    bulkEdit: (invoiceIds: string[], data: { terms?: string; notes?: string }) =>
      apiFetch<{ ok: boolean; updated: number; errors: number }>('/invoices/bulk-edit', {
        method: 'POST',
        body: JSON.stringify({ invoice_ids: invoiceIds, ...data }),
      }),
    emailQueueStatus: () =>
      apiFetch<{ sends: any[]; count: number }>('/invoices/email-queue-status'),
  },
  payments: {
    list: (invoiceId?: string, offset?: number, limit?: number) => {
      const p = new URLSearchParams();
      if (invoiceId) p.set('invoice_id', invoiceId);
      if (offset !== undefined) p.set('offset', String(offset));
      if (limit !== undefined) p.set('limit', String(limit));
      const qs = p.toString();
      return apiFetch<{
        payments: Payment[];
        total: number;
        offset: number;
        limit: number;
      }>(`/payments${qs ? `?${qs}` : ''}`);
    },
    record: (data: Partial<Payment>) =>
      apiFetch<{ ok: boolean }>('/payments', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    delete: (id: string) => apiFetch<{ ok: boolean }>(`/payments/${id}`, { method: 'DELETE' }),
  },
  appointments: {
    list: (offset?: number, limit?: number) => {
      const p = new URLSearchParams();
      if (offset !== undefined) p.set('offset', String(offset));
      if (limit !== undefined) p.set('limit', String(limit));
      const qs = p.toString();
      return apiFetch<{
        appointments: Appointment[];
        total: number;
        offset: number;
        limit: number;
      }>(`/appointments${qs ? `?${qs}` : ''}`);
    },
    create: (data: Partial<Appointment>) =>
      apiFetch<{ ok: boolean }>('/appointments', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    updateStatus: (id: string, status: string) =>
      apiFetch<{ ok: boolean }>(`/appointments/${id}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status }),
      }),
    delete: (id: string) => apiFetch<{ ok: boolean }>(`/appointments/${id}`, { method: 'DELETE' }),
    recurrence: {
      set: (id: string, rule: string) =>
        apiFetch<{ ok: boolean }>(`/appointments/${id}/recurrence`, {
          method: 'PUT',
          body: JSON.stringify({ recurrence_rule: rule }),
        }),
    },
    generateNext: (seriesId: string) =>
      apiFetch<{
        ok: boolean;
        start_time?: number;
        end_time?: number;
        error?: string;
      }>('/appointments/generate-next', {
        method: 'POST',
        body: JSON.stringify({ series_id: seriesId }),
      }),
    recurring: {
      list: () => apiFetch<{ series: Appointment[] }>('/appointments/recurring'),
    },
  },
  products: {
    list: (search?: string, category?: string, offset?: number, limit?: number) => {
      const p = new URLSearchParams();
      if (search) p.set('search', search);
      if (category) p.set('category', category);
      if (offset !== undefined) p.set('offset', String(offset));
      if (limit !== undefined) p.set('limit', String(limit));
      const qs = p.toString();
      return apiFetch<{
        products: Product[];
        total: number;
        offset: number;
        limit: number;
      }>(`/products${qs ? `?${qs}` : ''}`);
    },
    categories: () => apiFetch<{ categories: string[] }>('/products/categories'),
    create: (data: Partial<Product>) =>
      apiFetch<{ ok: boolean }>('/products', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    updateQuantity: (id: string, quantity_on_hand: number) =>
      apiFetch<{ ok: boolean }>(`/products/${id}/quantity`, {
        method: 'PUT',
        body: JSON.stringify({ quantity_on_hand }),
      }),
    delete: (id: string) => apiFetch<{ ok: boolean }>(`/products/${id}`, { method: 'DELETE' }),
    byBarcode: (barcode: string) =>
      apiFetch<{ product: Product }>(`/products/by-barcode/${encodeURIComponent(barcode)}`),
    adjustments: {
      list: (productId: string) =>
        apiFetch<{ adjustments: InventoryAdjustment[] }>(`/products/${productId}/adjustments`),
      create: (productId: string, data: Partial<InventoryAdjustment>) =>
        apiFetch<{ ok: boolean }>(`/products/${productId}/adjustments`, {
          method: 'POST',
          body: JSON.stringify(data),
        }),
    },
    lowStock: {
      list: () => apiFetch<{ products: Product[]; count: number }>('/products/low-stock'),
      notify: () =>
        apiFetch<{ ok: boolean; count?: number; notified?: string }>('/products/low-stock/notify', {
          method: 'POST',
        }),
    },
    transfer: (data: {
      source_product_id: string;
      destination_product_id: string;
      quantity: number;
      reference_id?: string;
      notes?: string;
    }) =>
      apiFetch<{ ok: boolean; quantity: number; reference: string }>('/products/transfer', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
  estimates: {
    list: (status?: string, offset?: number, limit?: number) => {
      const p = new URLSearchParams();
      if (status) p.set('status', status);
      if (offset !== undefined) p.set('offset', String(offset));
      if (limit !== undefined) p.set('limit', String(limit));
      const qs = p.toString();
      return apiFetch<{
        estimates: Estimate[];
        total: number;
        offset: number;
        limit: number;
      }>(`/estimates${qs ? `?${qs}` : ''}`);
    },
    create: (data: Partial<Estimate>) =>
      apiFetch<{ ok: boolean }>('/estimates', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    updateStatus: (id: string, status: string) =>
      apiFetch<{ ok: boolean }>(`/estimates/${id}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status }),
      }),
    lineItems: {
      list: (estimateId: string) =>
        apiFetch<{ line_items: EstimateLineItem[] }>(`/estimates/${estimateId}/line-items`),
      create: (estimateId: string, data: Partial<EstimateLineItem>) =>
        apiFetch<{ ok: boolean }>(`/estimates/${estimateId}/line-items`, {
          method: 'POST',
          body: JSON.stringify(data),
        }),
    },
    convert: (id: string) =>
      apiFetch<{ ok: boolean }>(`/estimates/${id}/convert`, { method: 'POST' }),
    delete: (id: string) => apiFetch<{ ok: boolean }>(`/estimates/${id}`, { method: 'DELETE' }),
  },
  purchaseOrders: {
    list: (offset?: number, limit?: number) => {
      const p = new URLSearchParams();
      if (offset !== undefined) p.set('offset', String(offset));
      if (limit !== undefined) p.set('limit', String(limit));
      const qs = p.toString();
      return apiFetch<{
        purchase_orders: PurchaseOrder[];
        total: number;
        offset: number;
        limit: number;
      }>(`/purchase-orders${qs ? `?${qs}` : ''}`);
    },
    get: (id: string) => apiFetch<{ purchase_order: PurchaseOrder }>(`/purchase-orders/${id}`),
    create: (data: Partial<PurchaseOrder>) =>
      apiFetch<{ ok: boolean }>('/purchase-orders', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/purchase-orders/${id}`, {
        method: 'DELETE',
      }),
    lineItems: {
      create: (poId: string, data: Partial<PurchaseOrderLineItem>) =>
        apiFetch<{ ok: boolean }>(`/purchase-orders/${poId}/line-items`, {
          method: 'POST',
          body: JSON.stringify(data),
        }),
      delete: (poId: string, itemId: string) =>
        apiFetch<{ ok: boolean }>(`/purchase-orders/${poId}/line-items/${itemId}`, {
          method: 'DELETE',
        }),
    },
    status: {
      update: (id: string, status: string) =>
        apiFetch<{ ok: boolean }>(`/purchase-orders/${id}/status`, {
          method: 'PUT',
          body: JSON.stringify({ status }),
        }),
    },
    receive: (poId: string, items: { id: string; received_quantity: number }[]) =>
      apiFetch<{ ok: boolean }>(`/purchase-orders/${poId}/receive`, {
        method: 'POST',
        body: JSON.stringify({ items }),
      }),
    submitForApproval: (poId: string) =>
      apiFetch<{ ok: boolean }>(`/purchase-orders/${poId}/submit-for-approval`, {
        method: 'POST',
      }),
    approve: (poId: string, userId: string) =>
      apiFetch<{ ok: boolean }>(`/purchase-orders/${poId}/approve`, {
        method: 'POST',
        body: JSON.stringify({ user_id: userId }),
      }),
    reject: (poId: string) =>
      apiFetch<{ ok: boolean }>(`/purchase-orders/${poId}/reject`, {
        method: 'POST',
      }),
  },
  users: {
    list: (offset?: number, limit?: number) => {
      const p = new URLSearchParams();
      if (offset !== undefined) p.set('offset', String(offset));
      if (limit !== undefined) p.set('limit', String(limit));
      const qs = p.toString();
      return apiFetch<{
        users: User[];
        total: number;
        offset: number;
        limit: number;
      }>(`/users${qs ? `?${qs}` : ''}`);
    },
    create: (data: Partial<User>) =>
      apiFetch<{ ok: boolean }>('/users', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
  settings: {
    mail: {
      get: () => apiFetch<{ configured: boolean; settings: MailSettings | null }>('/settings/mail'),
      save: (data: Partial<MailSettings>) =>
        apiFetch<{ ok: boolean }>('/settings/mail', {
          method: 'POST',
          body: JSON.stringify(data),
        }),
      test: () =>
        apiFetch<{ ok: boolean; message?: string; error?: string }>('/settings/mail/test', {
          method: 'POST',
        }),
    },
    sms: {
      get: () => apiFetch<{ configured: boolean; settings: SmsSettings | null }>('/settings/sms'),
      save: (data: { account_sid?: string; auth_token?: string; from_number?: string }) =>
        apiFetch<{ ok: boolean }>('/settings/sms', {
          method: 'POST',
          body: JSON.stringify(data),
        }),
      test: () =>
        apiFetch<{ ok: boolean; message?: string; error?: string }>('/settings/sms/test', {
          method: 'POST',
        }),
    },
    businessHours: {
      get: () =>
        apiFetch<{ configured: boolean; hours: BusinessHours }>('/settings/business-hours'),
      save: (data: BusinessHours) =>
        apiFetch<{ ok: boolean; hours: BusinessHours }>('/settings/business-hours', {
          method: 'POST',
          body: JSON.stringify(data),
        }),
    },
  },
  taxRates: {
    list: (offset?: number, limit?: number) => {
      const p = new URLSearchParams();
      if (offset !== undefined) p.set('offset', String(offset));
      if (limit !== undefined) p.set('limit', String(limit));
      const qs = p.toString();
      return apiFetch<{
        tax_rates: TaxRate[];
        total: number;
        offset: number;
        limit: number;
      }>(`/tax-rates${qs ? `?${qs}` : ''}`);
    },
    create: (data: { name: string; rate: number; is_default: boolean }) =>
      apiFetch<{ ok: boolean }>('/tax-rates', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id: string, data: { name: string; rate: number; is_default: boolean }) =>
      apiFetch<{ ok: boolean }>(`/tax-rates/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    delete: (id: string) => apiFetch<{ ok: boolean }>(`/tax-rates/${id}`, { method: 'DELETE' }),
    setInvoiceTaxRate: (invoiceId: string, taxRate: number) =>
      apiFetch<{ ok: boolean }>(`/invoices/${invoiceId}/tax-rate`, {
        method: 'PUT',
        body: JSON.stringify({ tax_rate: taxRate }),
      }),
  },
  reports: {
    get: () => apiFetch<ReportsData>('/reports'),
  },
  reportSchedules: {
    list: (offset = 0, limit = 50) =>
      apiFetch<{
        schedules: ScheduledReport[];
        total: number;
        offset: number;
        limit: number;
      }>(`/report-schedules?offset=${offset}&limit=${limit}`),
    create: (data: {
      name: string;
      report_type: string;
      schedule_frequency: string;
      recipients: string[];
      schedule_config?: Record<string, any>;
      filters?: Record<string, any>;
    }) =>
      apiFetch<{ ok: boolean; id: string; next_run_at: number }>('/report-schedules', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Record<string, any>) =>
      apiFetch<{ ok: boolean }>(`/report-schedules/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/report-schedules/${id}`, {
        method: 'DELETE',
      }),
    runNow: (id: string) =>
      apiFetch<{ ok: boolean; sent: number; total: number; errors: string[] }>(
        `/report-schedules/${id}/run-now`,
        {
          method: 'POST',
        },
      ),
  },
  auditLog: {
    list: (limit = 100, entity?: string, action?: string) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (entity) params.set('entity', entity);
      if (action) params.set('action', action);
      return apiFetch<{ entries: AuditLogEntry[] }>(`/audit-log?${params}`);
    },
  },
  export: {
    csv: (entity: string) => {
      const url = `${API_BASE}/export/${entity}`;
      // Trigger download by creating a temporary anchor
      const a = document.createElement('a');
      a.href = url;
      a.download = `${entity}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    },
  },
  health: {
    check: () => apiFetch<{ server: string; stdb: string; module: string }>('/health'),
    ready: () => apiFetch<{ status: string }>('/health/ready'),
  },
  customFields: {
    definitions: {
      list: (entityType?: string) =>
        apiFetch<{ definitions: CustomFieldDefinition[] }>(
          `/custom-field-definitions${entityType ? `?entity_type=${entityType}` : ''}`,
        ),
      create: (data: {
        entity_type: string;
        label: string;
        field_type: string;
        options?: string[];
        sort_order?: number;
        required?: boolean;
        active?: boolean;
      }) =>
        apiFetch<{ ok: boolean; id: string }>('/custom-field-definitions', {
          method: 'POST',
          body: JSON.stringify(data),
        }),
      update: (
        id: string,
        data: {
          label: string;
          field_type: string;
          options?: string[];
          sort_order?: number;
          required?: boolean;
          active?: boolean;
        },
      ) =>
        apiFetch<{ ok: boolean }>(`/custom-field-definitions/${id}`, {
          method: 'PUT',
          body: JSON.stringify(data),
        }),
      delete: (id: string) =>
        apiFetch<{ ok: boolean }>(`/custom-field-definitions/${id}`, {
          method: 'DELETE',
        }),
    },
    values: {
      get: (entityId: string) =>
        apiFetch<{ values: CustomFieldValue[] }>(`/custom-field-values/${entityId}`),
      set: (entityId: string, values: Record<string, string>) =>
        apiFetch<{ ok: boolean; count: number }>(`/custom-field-values/${entityId}`, {
          method: 'PUT',
          body: JSON.stringify({ values }),
        }),
    },
  },
  import: {
    customers: (file: File) => {
      const form = new FormData();
      form.append('file', file);
      return fetch(`${API_BASE}/import/customers`, {
        method: 'POST',
        body: form,
      }).then((r) => r.json()) as Promise<{
        imported: number;
        errors: string[];
        file: string;
      }>;
    },
    products: (file: File) => {
      const form = new FormData();
      form.append('file', file);
      return fetch(`${API_BASE}/import/products`, {
        method: 'POST',
        body: form,
      }).then((r) => r.json()) as Promise<{
        imported: number;
        errors: string[];
        file: string;
      }>;
    },
  },
  tenants: {
    list: () => apiFetch<{ tenants: Tenant[] }>('/tenants'),
    get: (id: string) => apiFetch<{ tenant: Tenant }>(`/tenants/${id}`),
    create: (data: { name: string; slug?: string }) =>
      apiFetch<{ ok: boolean }>('/tenants', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (
      id: string,
      data: {
        name?: string;
        slug?: string;
        logo_url?: string;
        settings?: string;
      },
    ) =>
      apiFetch<{ ok: boolean }>(`/tenants/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    delete: (id: string) => apiFetch<{ ok: boolean }>(`/tenants/${id}`, { method: 'DELETE' }),
    addMember: (tenantId: string, data: { username: string; role: string }) =>
      apiFetch<{ ok: boolean }>(`/tenants/${tenantId}/members`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    removeMember: (tenantId: string, memberId: string) =>
      apiFetch<{ ok: boolean }>(`/tenants/${tenantId}/members/${memberId}`, {
        method: 'DELETE',
      }),
    updateMemberRole: (tenantId: string, memberId: string, role: string) =>
      apiFetch<{ ok: boolean }>(`/tenants/${tenantId}/members/${memberId}`, {
        method: 'PUT',
        body: JSON.stringify({ role }),
      }),
    migrate: (data: { name?: string; slug?: string }) =>
      apiFetch<{
        ok: boolean;
        tenant_id?: string;
        users_migrated?: number;
        tables_updated?: Record<string, boolean>;
      }>('/tenants/migrate', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
  webhooks: {
    list: () => apiFetch<{ subscriptions: WebhookSubscription[] }>('/webhook-subscriptions'),
    create: (data: { url: string; events: string; secret?: string }) =>
      apiFetch<{ ok: boolean }>('/webhook-subscriptions', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (
      id: string,
      data: { url: string; events?: string; secret?: string; active?: boolean },
    ) =>
      apiFetch<{ ok: boolean }>(`/webhook-subscriptions/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/webhook-subscriptions/${id}`, {
        method: 'DELETE',
      }),
    test: (id: string) =>
      apiFetch<{ ok: boolean; status_code?: number; error?: string }>(
        `/webhook-subscriptions/${id}/test`,
        { method: 'POST' },
      ),
  },
  recurringInvoices: {
    list: () => apiFetch<{ rules: RecurringInvoiceRule[] }>('/recurring-invoices'),
    create: (data: any) =>
      apiFetch<{ ok: boolean }>('/recurring-invoices', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    update: (id: string, data: any) =>
      apiFetch<{ ok: boolean }>(`/recurring-invoices/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/recurring-invoices/${id}`, {
        method: 'DELETE',
      }),
    generate: () =>
      apiFetch<{ ok: boolean }>('/recurring-invoices/generate', {
        method: 'POST',
      }),
  },
  paymentMethods: {
    list: (customerId?: string) => {
      const qs = customerId ? `?customer_id=${encodeURIComponent(customerId)}` : '';
      return apiFetch<{ payment_methods: SavedPaymentMethod[] }>(`/payment-methods${qs}`);
    },
    createSetupIntent: (customer_id: string) =>
      apiFetch<{ client_secret: string; id: string }>('/payment-methods/setup-intent', {
        method: 'POST',
        body: JSON.stringify({ customer_id }),
      }),
    save: (data: any) =>
      apiFetch<{ ok: boolean }>('/payment-methods', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    setDefault: (id: string, customer_id: string) =>
      apiFetch<{ ok: boolean }>(`/payment-methods/${id}/default`, {
        method: 'PUT',
        body: JSON.stringify({ customer_id }),
      }),
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/payment-methods/${id}`, { method: 'DELETE' }),
  },
  pos: {
    list: (offset?: number, limit?: number) => {
      const p = new URLSearchParams();
      if (offset !== undefined) p.set('offset', String(offset));
      if (limit !== undefined) p.set('limit', String(limit));
      const qs = p.toString();
      return apiFetch<{
        sales: POSCounterSale[];
        total: number;
        offset: number;
        limit: number;
      }>(`/pos/sales${qs ? `?${qs}` : ''}`);
    },
    get: (id: string) => apiFetch<{ sale: POSCounterSaleDetail }>(`/pos/sales/${id}`),
    create: (data: Partial<POSCounterSale>) =>
      apiFetch<{ ok: boolean }>('/pos/create', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    addItem: (data: POSAddItemPayload) =>
      apiFetch<{ ok: boolean }>('/pos/items', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    refund: (id: string) => apiFetch<{ ok: boolean }>(`/pos/refund/${id}`, { method: 'POST' }),
    delete: (id: string) => apiFetch<{ ok: boolean }>(`/pos/sales/${id}`, { method: 'DELETE' }),
    receipts: (offset?: number, limit?: number) => {
      const p = new URLSearchParams();
      if (offset !== undefined) p.set('offset', String(offset));
      if (limit !== undefined) p.set('limit', String(limit));
      const qs = p.toString();
      return apiFetch<{
        receipts: POSCounterSale[];
        total: number;
        offset: number;
        limit: number;
      }>(`/pos/receipts${qs ? `?${qs}` : ''}`);
    },
  },
  auth: {
    setup2FA: () =>
      apiFetch<{ secret: string; provisioning_uri: string }>('/auth/setup-2fa', {
        method: 'POST',
      }),
    verify2FA: (code: string) =>
      apiFetch<{ ok: boolean; message: string }>('/auth/verify-2fa', {
        method: 'POST',
        body: JSON.stringify({ code }),
      }),
    disable2FA: (code: string) =>
      apiFetch<{ ok: boolean; message: string }>('/auth/disable-2fa', {
        method: 'POST',
        body: JSON.stringify({ code }),
      }),
    setPin: (pin: string) =>
      apiFetch<{ ok: boolean }>('/auth/set-pin', {
        method: 'POST',
        body: JSON.stringify({ pin }),
      }),
    posLogin: (user_id: string, pin: string) =>
      apiFetch<{
        token: string;
        user: {
          id: string;
          name: string;
          email: string;
          role: string;
          tenant_id: string;
        };
      }>('/auth/pos-login', {
        method: 'POST',
        body: JSON.stringify({ user_id, pin }),
      }),
  },
  userSettings: {
    get: () =>
      apiFetch<{
        settings: {
          user_id: string;
          theme: string;
          default_ticket_status: string;
          created_at: number;
          updated_at: number;
        } | null;
      }>('/users/settings'),
    update: (data: { theme: string; default_ticket_status: string }) =>
      apiFetch<{ ok: boolean }>('/users/settings', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
  },
};
