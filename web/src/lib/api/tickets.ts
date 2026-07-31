import { apiFetch, buildPaginationParams } from "./client";
import type { Ticket, TicketNote, TicketSlaBreach, TicketTimer } from "./types";

export const tickets = {
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
			tickets: Ticket[];
			total: number;
			offset: number;
			limit: number;
		}>(`/tickets${qs ? `?${qs}` : ""}`);
	},
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
	sla: {
		breaches: () =>
			apiFetch<{ breaches: TicketSlaBreach[]; count: number }>(
				"/tickets/sla-breached",
			),
		targets: () =>
			apiFetch<{ targets: Record<string, number> }>("/tickets/sla-targets"),
		settings: () =>
			apiFetch<{ targets: Record<string, number>; updated_at: number }>(
				"/tickets/sla-settings",
			),
		save: (targets: Record<string, number>) =>
			apiFetch<{ targets: Record<string, number>; ok: boolean }>(
				"/tickets/sla-settings",
				{
					method: "POST",
					body: JSON.stringify({ targets }),
				},
			),
	},
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
};
