import { apiFetch, buildPaginationParams } from "./client";
import type {
	POSCounterSale,
	POSCounterSaleDetail,
	POSCounterSaleLineItem,
	POSAddItemPayload,
} from "./types";

export const pos = {
	list: (offset?: number, limit?: number) => {
		const p = new URLSearchParams();
		if (offset !== undefined) p.set("offset", String(offset));
		if (limit !== undefined) p.set("limit", String(limit));
		const qs = p.toString();
		return apiFetch<{
			sales: POSCounterSale[];
			total: number;
			offset: number;
			limit: number;
		}>(`/pos/sales${qs ? `?${qs}` : ""}`);
	},
	get: (id: string) =>
		apiFetch<{ sale: POSCounterSaleDetail }>(`/pos/sales/${id}`),
	create: (data: Partial<POSCounterSale>) =>
		apiFetch<{ ok: boolean }>("/pos/create", {
			method: "POST",
			body: JSON.stringify(data),
		}),
	addItem: (data: POSAddItemPayload) =>
		apiFetch<{ ok: boolean }>("/pos/items", {
			method: "POST",
			body: JSON.stringify(data),
		}),
	refund: (id: string) =>
		apiFetch<{ ok: boolean }>(`/pos/refund/${id}`, { method: "POST" }),
	delete: (id: string) =>
		apiFetch<{ ok: boolean }>(`/pos/sales/${id}`, { method: "DELETE" }),
	receipts: (offset?: number, limit?: number) => {
		const p = new URLSearchParams();
		if (offset !== undefined) p.set("offset", String(offset));
		if (limit !== undefined) p.set("limit", String(limit));
		const qs = p.toString();
		return apiFetch<{
			receipts: POSCounterSale[];
			total: number;
			offset: number;
			limit: number;
		}>(`/pos/receipts${qs ? `?${qs}` : ""}`);
	},
};
