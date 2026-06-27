const API_BASE = "/api";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
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

export interface Ticket {
  id: string;
  customer_id: string;
  ticket_number: number;
  title: string;
  description: string;
  device_type: string;
  device_model: string;
  device_serial: string;
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
  notes: string;
  terms: string;
  due_date: number;
  created_at: number;
  updated_at: number;
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

export interface Payment {
  id: string;
  invoice_id: string;
  customer_id: string;
  amount: number;
  method: string;
  reference: string;
  notes: string;
  created_at: number;
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
  created_at: number;
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
  subtotal: number;
  tax_amount: number;
  total: number;
  notes: string;
  created_at: number;
  line_items?: PurchaseOrderLineItem[];
  receipt_progress?: number;
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
  email: string;
  role: string;
  active: boolean;
  created_at: number;
}

export interface DashboardStats {
  total_customers: number;
  total_tickets: number;
  open_tickets: number;
  revenue: number;
  pending_revenue: number;
  upcoming_appointments: number;
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

export interface ReportsData {
  revenue_by_month: { month: string; revenue: number }[];
  ticket_by_status: { status: string; count: number }[];
  invoice_by_status: { status: string; count: number }[];
  appointments_by_month: { month: string; appointments: number }[];
  totals: {
    total_revenue: number;
    total_tickets: number;
    open_tickets: number;
    total_sent: number;
    total_paid: number;
  };
}

// ── API client ──

export const api = {
  stats: {
    get: () => apiFetch<DashboardStats>("/stats"),
  },
  customers: {
    list: (search?: string) =>
      apiFetch<{ customers: Customer[] }>(
        `/customers${search ? `?search=${encodeURIComponent(search)}` : ""}`
      ),
    create: (data: Partial<Customer>) =>
      apiFetch<{ ok: boolean }>("/customers", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: Partial<Customer>) =>
      apiFetch<{ ok: boolean }>(`/customers/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/customers/${id}`, { method: "DELETE" }),
  },
  tickets: {
    list: (status?: string) =>
      apiFetch<{ tickets: Ticket[] }>(
        `/tickets${status ? `?status=${status}` : ""}`
      ),
    create: (data: Partial<Ticket>) =>
      apiFetch<{ ok: boolean }>("/tickets", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    updateStatus: (id: string, status: string) =>
      apiFetch<{ ok: boolean }>(`/tickets/${id}/status`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      }),
    assign: (id: string, assigned_user_id: string) =>
      apiFetch<{ ok: boolean }>(`/tickets/${id}/assign`, {
        method: "PUT",
        body: JSON.stringify({ assigned_user_id }),
      }),
    notes: {
      list: (ticketId: string) =>
        apiFetch<{ notes: TicketNote[] }>(`/tickets/${ticketId}/notes`),
      create: (ticketId: string, data: Partial<TicketNote>) =>
        apiFetch<{ ok: boolean }>(`/tickets/${ticketId}/notes`, {
          method: "POST",
          body: JSON.stringify(data),
        }),
    },
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/tickets/${id}`, { method: "DELETE" }),
    timers: {
      list: (ticketId: string) =>
        apiFetch<{ timers: TicketTimer[] }>(`/tickets/${ticketId}/timers`),
      start: (ticketId: string, userId: string) =>
        apiFetch<{ ok: boolean }>(`/tickets/${ticketId}/timers/start`, {
          method: "POST",
          body: JSON.stringify({ user_id: userId }),
        }),
      stop: (timerId: string) =>
        apiFetch<{ ok: boolean }>(`/timers/${timerId}/stop`, { method: "POST" }),
      delete: (timerId: string) =>
        apiFetch<{ ok: boolean }>(`/timers/${timerId}`, { method: "DELETE" }),
    },
  },
  invoices: {
    list: (status?: string) =>
      apiFetch<{ invoices: Invoice[] }>(
        `/invoices${status ? `?status=${status}` : ""}`
      ),
    create: (data: Partial<Invoice>) =>
      apiFetch<{ ok: boolean }>("/invoices", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    updateStatus: (id: string, status: string) =>
      apiFetch<{ ok: boolean }>(`/invoices/${id}/status`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      }),
    lineItems: {
      list: (invoiceId: string) =>
        apiFetch<{ line_items: InvoiceLineItem[] }>(
          `/invoices/${invoiceId}/line-items`
        ),
      create: (invoiceId: string, data: Partial<InvoiceLineItem>) =>
        apiFetch<{ ok: boolean }>(`/invoices/${invoiceId}/line-items`, {
          method: "POST",
          body: JSON.stringify(data),
        }),
      delete: (invoiceId: string, itemId: string) =>
        apiFetch<{ ok: boolean }>(
          `/invoices/${invoiceId}/line-items/${itemId}`,
          { method: "DELETE" }
        ),
    },
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/invoices/${id}`, { method: "DELETE" }),
  },
  payments: {
    list: (invoiceId?: string) =>
      apiFetch<{ payments: Payment[] }>(
        `/payments${invoiceId ? `?invoice_id=${invoiceId}` : ""}`
      ),
    record: (data: Partial<Payment>) =>
      apiFetch<{ ok: boolean }>("/payments", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/payments/${id}`, { method: "DELETE" }),
  },
  appointments: {
    list: () => apiFetch<{ appointments: Appointment[] }>("/appointments"),
    create: (data: Partial<Appointment>) =>
      apiFetch<{ ok: boolean }>("/appointments", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    updateStatus: (id: string, status: string) =>
      apiFetch<{ ok: boolean }>(`/appointments/${id}/status`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      }),
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/appointments/${id}`, { method: "DELETE" }),
  },
  products: {
    list: (search?: string) =>
      apiFetch<{ products: Product[] }>(
        `/products${search ? `?search=${encodeURIComponent(search)}` : ""}`
      ),
    create: (data: Partial<Product>) =>
      apiFetch<{ ok: boolean }>("/products", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    updateQuantity: (id: string, quantity_on_hand: number) =>
      apiFetch<{ ok: boolean }>(`/products/${id}/quantity`, {
        method: "PUT",
        body: JSON.stringify({ quantity_on_hand }),
      }),
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/products/${id}`, { method: "DELETE" }),
    adjustments: {
      list: (productId: string) =>
        apiFetch<{ adjustments: InventoryAdjustment[] }>(
          `/products/${productId}/adjustments`
        ),
      create: (productId: string, data: Partial<InventoryAdjustment>) =>
        apiFetch<{ ok: boolean }>(`/products/${productId}/adjustments`, {
          method: "POST",
          body: JSON.stringify(data),
        }),
    },
  },
  estimates: {
    list: (status?: string) =>
      apiFetch<{ estimates: Estimate[] }>(
        `/estimates${status ? `?status=${status}` : ""}`
      ),
    create: (data: Partial<Estimate>) =>
      apiFetch<{ ok: boolean }>("/estimates", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    updateStatus: (id: string, status: string) =>
      apiFetch<{ ok: boolean }>(`/estimates/${id}/status`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      }),
    lineItems: {
      list: (estimateId: string) =>
        apiFetch<{ line_items: EstimateLineItem[] }>(
          `/estimates/${estimateId}/line-items`
        ),
      create: (estimateId: string, data: Partial<EstimateLineItem>) =>
        apiFetch<{ ok: boolean }>(`/estimates/${estimateId}/line-items`, {
          method: "POST",
          body: JSON.stringify(data),
        }),
    },
    convert: (id: string) =>
      apiFetch<{ ok: boolean }>(`/estimates/${id}/convert`, { method: "POST" }),
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/estimates/${id}`, { method: "DELETE" }),
  },
  purchaseOrders: {
    list: () =>
      apiFetch<{ purchase_orders: PurchaseOrder[] }>("/purchase-orders"),
    get: (id: string) =>
      apiFetch<{ purchase_order: PurchaseOrder }>(`/purchase-orders/${id}`),
    create: (data: Partial<PurchaseOrder>) =>
      apiFetch<{ ok: boolean }>("/purchase-orders", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/purchase-orders/${id}`, {
        method: "DELETE",
      }),
    lineItems: {
      create: (poId: string, data: Partial<PurchaseOrderLineItem>) =>
        apiFetch<{ ok: boolean }>(`/purchase-orders/${poId}/line-items`, {
          method: "POST",
          body: JSON.stringify(data),
        }),
      delete: (poId: string, itemId: string) =>
        apiFetch<{ ok: boolean }>(
          `/purchase-orders/${poId}/line-items/${itemId}`,
          { method: "DELETE" }
        ),
    },
    status: {
      update: (id: string, status: string) =>
        apiFetch<{ ok: boolean }>(`/purchase-orders/${id}/status`, {
          method: "PUT",
          body: JSON.stringify({ status }),
        }),
    },
    receive: (poId: string, items: { id: string; received_quantity: number }[]) =>
      apiFetch<{ ok: boolean }>(`/purchase-orders/${poId}/receive`, {
        method: "POST",
        body: JSON.stringify({ items }),
      }),
  },
  users: {
    list: () => apiFetch<{ users: User[] }>("/users"),
    create: (data: Partial<User>) =>
      apiFetch<{ ok: boolean }>("/users", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
  settings: {
    mail: {
      get: () => apiFetch<{ configured: boolean; settings: MailSettings | null }>("/settings/mail"),
      save: (data: Partial<MailSettings>) =>
        apiFetch<{ ok: boolean }>("/settings/mail", {
          method: "POST",
          body: JSON.stringify(data),
        }),
      test: () =>
        apiFetch<{ ok: boolean; message?: string; error?: string }>("/settings/mail/test", {
          method: "POST",
        }),
    },
  },
  taxRates: {
    list: () => apiFetch<{ tax_rates: TaxRate[] }>("/tax-rates"),
    create: (data: { name: string; rate: number; is_default: boolean }) =>
      apiFetch<{ ok: boolean }>("/tax-rates", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: { name: string; rate: number; is_default: boolean }) =>
      apiFetch<{ ok: boolean }>(`/tax-rates/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/tax-rates/${id}`, { method: "DELETE" }),
    setInvoiceTaxRate: (invoiceId: string, taxRate: number) =>
      apiFetch<{ ok: boolean }>(`/invoices/${invoiceId}/tax-rate`, {
        method: "PUT",
        body: JSON.stringify({ tax_rate: taxRate }),
      }),
  },
  reports: {
    get: () => apiFetch<ReportsData>("/reports"),
  },
  auditLog: {
    list: (limit = 100, entity?: string, action?: string) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (entity) params.set("entity", entity);
      if (action) params.set("action", action);
      return apiFetch<{ entries: any[] }>(`/audit-log?${params}`);
    },
  },
  export: {
    csv: (entity: string) => {
      const url = `${API_BASE}/export/${entity}`;
      // Trigger download by creating a temporary anchor
      const a = document.createElement("a");
      a.href = url;
      a.download = `${entity}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    },
  },
  import: {
    customers: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return fetch(`${API_BASE}/import/customers`, { method: "POST", body: form }).then(r => r.json()) as Promise<{ imported: number; errors: string[]; file: string }>;
    },
    products: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return fetch(`${API_BASE}/import/products`, { method: "POST", body: form }).then(r => r.json()) as Promise<{ imported: number; errors: string[]; file: string }>;
    },
  },
};
