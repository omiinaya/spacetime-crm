import { apiFetch } from "./client";
import type {
	Invoice,
	InvoiceLineItem,
	InvoiceSummary,
	RecurringInvoiceRule,
} from "./types";

export const invoices = {
	list: (
		status?: string,
		customerId?: string,
		offset?: number,
		limit?: number,
	) => {
		const p = new URLSearchParams();
		if (status) p.set("status", status);
		if (customerId) p.set("customer_id", customerId);
		if (offset !== undefined) p.set("offset", String(offset));
		if (limit !== undefined) p.set("limit", String(limit));
		const qs = p.toString();
		return apiFetch<{
			invoices: Invoice[];
			total: number;
			offset: number;
			limit: number;
		}>(`/invoices${qs ? `?${qs}` : ""}`);
	},
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
				`/invoices/${invoiceId}/line-items`,
			),
		create: (invoiceId: string, data: Partial<InvoiceLineItem>) =>
			apiFetch<{ ok: boolean }>(`/invoices/${invoiceId}/line-items`, {
				method: "POST",
				body: JSON.stringify(data),
			}),
		delete: (invoiceId: string, itemId: string) =>
			apiFetch<{ ok: boolean }>(`/invoices/${invoiceId}/line-items/${itemId}`, {
				method: "DELETE",
			}),
	},
	delete: (id: string) =>
		apiFetch<{ ok: boolean }>(`/invoices/${id}`, { method: "DELETE" }),
	overdueCount: () =>
		apiFetch<{ count: number; total: number }>("/invoices/overdue-count"),
	triggerOverdueCheck: () =>
		apiFetch<{ ok: boolean }>("/invoices/trigger-overdue-check", {
			method: "POST",
		}),
	summary: () => apiFetch<InvoiceSummary>("/invoices/summary"),
	bulkStatusUpdate: (invoiceIds: string[], status: string) =>
		apiFetch<{ ok: boolean; updated: number; errors: number }>(
			"/invoices/bulk-status-update",
			{
				method: "POST",
				body: JSON.stringify({ invoice_ids: invoiceIds, status }),
			},
		),
	sendOverdueReminders: () =>
		apiFetch<{ ok: boolean; email: number; sms: number; total: number }>(
			"/invoices/send-overdue-reminders",
			{ method: "POST" },
		),
	sendEmail: (invoiceId: string) =>
		apiFetch<{ ok: boolean; sent_to: string; invoice_number: number }>(
			"/invoices/send-email",
			{
				method: "POST",
				body: JSON.stringify({ invoice_id: invoiceId }),
			},
		),
	sendBatchEmail: (invoiceIds: string[]) =>
		apiFetch<{
			ok: boolean;
			sent: number;
			failed: number;
			skipped: number;
			details: any[];
		}>("/invoices/send-batch-email", {
			method: "POST",
			body: JSON.stringify({ invoice_ids: invoiceIds }),
		}),
	bulkEdit: (invoiceIds: string[], data: { terms?: string; notes?: string }) =>
		apiFetch<{ ok: boolean; updated: number; errors: number }>(
			"/invoices/bulk-edit",
			{
				method: "POST",
				body: JSON.stringify({ invoice_ids: invoiceIds, ...data }),
			},
		),
	emailQueueStatus: () =>
		apiFetch<{ sends: any[]; count: number }>("/invoices/email-queue-status"),
};

export const recurringInvoices = {
	list: () =>
		apiFetch<{ rules: RecurringInvoiceRule[] }>("/recurring-invoices"),
	create: (data: any) =>
		apiFetch<{ ok: boolean }>("/recurring-invoices", {
			method: "POST",
			body: JSON.stringify(data),
		}),
	update: (id: string, data: any) =>
		apiFetch<{ ok: boolean }>(`/recurring-invoices/${id}`, {
			method: "PUT",
			body: JSON.stringify(data),
		}),
	delete: (id: string) =>
		apiFetch<{ ok: boolean }>(`/recurring-invoices/${id}`, {
			method: "DELETE",
		}),
	generate: () =>
		apiFetch<{ ok: boolean }>("/recurring-invoices/generate", {
			method: "POST",
		}),
};
