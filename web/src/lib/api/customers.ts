import { apiFetch, buildPaginationParams } from "./client";
import type { Customer, CustomerGeoLocation } from "./types";

export const customers = {
	list: (search?: string, offset?: number, limit?: number) => {
		const p = new URLSearchParams();
		if (search) p.set("search", search);
		if (offset !== undefined) p.set("offset", String(offset));
		if (limit !== undefined) p.set("limit", String(limit));
		const qs = p.toString();
		return apiFetch<{
			customers: Customer[];
			total: number;
			offset: number;
			limit: number;
		}>(`/customers${qs ? `?${qs}` : ""}`);
	},
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
	geolocations: {
		list: () =>
			apiFetch<{ locations: CustomerGeoLocation[] }>("/customers/geolocations"),
		geocode: (customerId: string) =>
			apiFetch<{
				ok: boolean;
				latitude?: number;
				longitude?: number;
				display_name?: string;
				error?: string;
			}>(`/customers/${customerId}/geocode`, { method: "POST" }),
		geocodeAll: () =>
			apiFetch<{ geocoded: number; results: any[] }>("/customers/geocode-all", {
				method: "POST",
			}),
	},
	setPortalPassword: (id: string, password: string) =>
		apiFetch<{ ok: boolean }>(`/customers/${id}/portal-password`, {
			method: "POST",
			body: JSON.stringify({ password }),
		}),
	duplicates: () =>
		apiFetch<{
			duplicates: { field: string; value: string; customers: Customer[] }[];
			count: number;
		}>("/customers/duplicates"),
};
