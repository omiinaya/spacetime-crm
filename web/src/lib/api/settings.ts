import { apiFetch, buildPaginationParams } from "./client";
import type {
	MailSettings,
	SmsSettings,
	BusinessHours,
	TaxRate,
} from "./types";

export const settings = {
	mail: {
		get: () =>
			apiFetch<{ configured: boolean; settings: MailSettings | null }>(
				"/settings/mail",
			),
		save: (data: Partial<MailSettings>) =>
			apiFetch<{ ok: boolean }>("/settings/mail", {
				method: "POST",
				body: JSON.stringify(data),
			}),
		test: () =>
			apiFetch<{ ok: boolean; message?: string; error?: string }>(
				"/settings/mail/test",
				{
					method: "POST",
				},
			),
	},
	sms: {
		get: () =>
			apiFetch<{ configured: boolean; settings: SmsSettings | null }>(
				"/settings/sms",
			),
		save: (data: {
			account_sid?: string;
			auth_token?: string;
			from_number?: string;
		}) =>
			apiFetch<{ ok: boolean }>("/settings/sms", {
				method: "POST",
				body: JSON.stringify(data),
			}),
		test: () =>
			apiFetch<{ ok: boolean; message?: string; error?: string }>(
				"/settings/sms/test",
				{
					method: "POST",
				},
			),
	},
	businessHours: {
		get: () =>
			apiFetch<{ configured: boolean; hours: BusinessHours }>(
				"/settings/business-hours",
			),
		save: (data: BusinessHours) =>
			apiFetch<{ ok: boolean; hours: BusinessHours }>(
				"/settings/business-hours",
				{
					method: "POST",
					body: JSON.stringify(data),
				},
			),
	},
	app: {
		get: () =>
			apiFetch<{ config: { revenue_target: number } }>("/settings/app"),
		save: (data: { revenue_target: number }) =>
			apiFetch<{ ok: boolean; config: { revenue_target: number } }>(
				"/settings/app",
				{
					method: "POST",
					body: JSON.stringify(data),
				},
			),
	},
};

export const taxRates = {
	list: (offset?: number, limit?: number) => {
		const p = new URLSearchParams();
		if (offset !== undefined) p.set("offset", String(offset));
		if (limit !== undefined) p.set("limit", String(limit));
		const qs = p.toString();
		return apiFetch<{
			tax_rates: TaxRate[];
			total: number;
			offset: number;
			limit: number;
		}>(`/tax-rates${qs ? `?${qs}` : ""}`);
	},
	create: (data: { name: string; rate: number; is_default: boolean }) =>
		apiFetch<{ ok: boolean }>("/tax-rates", {
			method: "POST",
			body: JSON.stringify(data),
		}),
	update: (
		id: string,
		data: { name: string; rate: number; is_default: boolean },
	) =>
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
};
