import { apiFetch, buildPaginationParams } from "./client";
import type { Payment, SavedPaymentMethod } from "./types";

export const payments = {
	list: (invoiceId?: string, offset?: number, limit?: number) => {
		const p = new URLSearchParams();
		if (invoiceId) p.set("invoice_id", invoiceId);
		if (offset !== undefined) p.set("offset", String(offset));
		if (limit !== undefined) p.set("limit", String(limit));
		const qs = p.toString();
		return apiFetch<{
			payments: Payment[];
			total: number;
			offset: number;
			limit: number;
		}>(`/payments${qs ? `?${qs}` : ""}`);
	},
	record: (data: Partial<Payment>) =>
		apiFetch<{ ok: boolean }>("/payments", {
			method: "POST",
			body: JSON.stringify(data),
		}),
	delete: (id: string) =>
		apiFetch<{ ok: boolean }>(`/payments/${id}`, { method: "DELETE" }),
};

export const paymentMethods = {
	list: (customerId?: string) => {
		const qs = customerId
			? `?customer_id=${encodeURIComponent(customerId)}`
			: "";
		return apiFetch<{ payment_methods: SavedPaymentMethod[] }>(
			`/payment-methods${qs}`,
		);
	},
	createSetupIntent: (customer_id: string) =>
		apiFetch<{ client_secret: string; id: string }>(
			"/payment-methods/setup-intent",
			{
				method: "POST",
				body: JSON.stringify({ customer_id }),
			},
		),
	save: (data: any) =>
		apiFetch<{ ok: boolean }>("/payment-methods", {
			method: "POST",
			body: JSON.stringify(data),
		}),
	setDefault: (id: string, customer_id: string) =>
		apiFetch<{ ok: boolean }>(`/payment-methods/${id}/default`, {
			method: "PUT",
			body: JSON.stringify({ customer_id }),
		}),
	delete: (id: string) =>
		apiFetch<{ ok: boolean }>(`/payment-methods/${id}`, { method: "DELETE" }),
};
