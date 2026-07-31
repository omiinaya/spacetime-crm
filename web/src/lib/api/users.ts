import { apiFetch, buildPaginationParams } from "./client";
import type { User } from "./types";

export const users = {
	list: (offset?: number, limit?: number) => {
		const p = new URLSearchParams();
		if (offset !== undefined) p.set("offset", String(offset));
		if (limit !== undefined) p.set("limit", String(limit));
		const qs = p.toString();
		return apiFetch<{
			users: User[];
			total: number;
			offset: number;
			limit: number;
		}>(`/users${qs ? `?${qs}` : ""}`);
	},
	create: (data: Partial<User>) =>
		apiFetch<{ ok: boolean }>("/users", {
			method: "POST",
			body: JSON.stringify(data),
		}),
};

export const userSettings = {
	get: () =>
		apiFetch<{
			settings: {
				user_id: string;
				theme: string;
				default_ticket_status: string;
				created_at: number;
				updated_at: number;
			} | null;
		}>("/users/settings"),
	update: (data: { theme: string; default_ticket_status: string }) =>
		apiFetch<{ ok: boolean }>("/users/settings", {
			method: "PUT",
			body: JSON.stringify(data),
		}),
};
