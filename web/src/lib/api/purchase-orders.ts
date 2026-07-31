import { apiFetch, buildPaginationParams } from "./client";
import type { PurchaseOrder, PurchaseOrderLineItem } from "./types";

export const purchaseOrders = {
	list: (offset?: number, limit?: number) => {
		const p = new URLSearchParams();
		if (offset !== undefined) p.set("offset", String(offset));
		if (limit !== undefined) p.set("limit", String(limit));
		const qs = p.toString();
		return apiFetch<{
			purchase_orders: PurchaseOrder[];
			total: number;
			offset: number;
			limit: number;
		}>(`/purchase-orders${qs ? `?${qs}` : ""}`);
	},
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
				{
					method: "DELETE",
				},
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
	submitForApproval: (poId: string) =>
		apiFetch<{ ok: boolean }>(`/purchase-orders/${poId}/submit-for-approval`, {
			method: "POST",
		}),
	approve: (poId: string, userId: string) =>
		apiFetch<{ ok: boolean }>(`/purchase-orders/${poId}/approve`, {
			method: "POST",
			body: JSON.stringify({ user_id: userId }),
		}),
	reject: (poId: string) =>
		apiFetch<{ ok: boolean }>(`/purchase-orders/${poId}/reject`, {
			method: "POST",
		}),
};
