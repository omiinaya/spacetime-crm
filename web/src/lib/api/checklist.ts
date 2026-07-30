import { apiFetch, buildPaginationParams } from "./client";
import type { ChecklistTemplate, TicketChecklistItem } from "./types";

export const checklist = {
  templates: {
    list: (offset?: number, limit?: number) => {
      const p = new URLSearchParams();
      if (offset !== undefined) p.set("offset", String(offset));
      if (limit !== undefined) p.set("limit", String(limit));
      const qs = p.toString();
      return apiFetch<{
        templates: ChecklistTemplate[];
        total: number;
        offset: number;
        limit: number;
      }>(`/checklist-templates${qs ? `?${qs}` : ""}`);
    },
    create: (data: { name: string; description?: string; items?: any[] }) =>
      apiFetch<{ ok: boolean }>("/checklist-templates", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (
      id: string,
      data: { name: string; description?: string; items?: any[] },
    ) =>
      apiFetch<{ ok: boolean }>(`/checklist-templates/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/checklist-templates/${id}`, {
        method: "DELETE",
      }),
  },
  ticket: {
    list: (ticketId: string) =>
      apiFetch<{ items: TicketChecklistItem[] }>(
        `/tickets/${ticketId}/checklist`,
      ),
    apply: (ticketId: string, templateId: string) =>
      apiFetch<{ ok: boolean }>(`/tickets/${ticketId}/checklist/apply`, {
        method: "POST",
        body: JSON.stringify({ template_id: templateId }),
      }),
    toggle: (ticketId: string, itemId: string, completed: boolean) =>
      apiFetch<{ ok: boolean }>(`/tickets/${ticketId}/checklist/${itemId}`, {
        method: "PUT",
        body: JSON.stringify({ completed }),
      }),
    clear: (ticketId: string) =>
      apiFetch<{ ok: boolean }>(`/tickets/${ticketId}/checklist`, {
        method: "DELETE",
      }),
  },
};
