import { apiFetch } from "./client";
import type { ReportsData, ScheduledReport, AuditLogEntry } from "./types";

export const reports = {
  get: () => apiFetch<ReportsData>("/reports"),
};

export const reportSchedules = {
  list: (offset = 0, limit = 50) =>
    apiFetch<{
      schedules: ScheduledReport[];
      total: number;
      offset: number;
      limit: number;
    }>(`/report-schedules?offset=${offset}&limit=${limit}`),
  create: (data: {
    name: string;
    report_type: string;
    schedule_frequency: string;
    recipients: string[];
    schedule_config?: Record<string, any>;
    filters?: Record<string, any>;
  }) =>
    apiFetch<{ ok: boolean; id: string; next_run_at: number }>(
      "/report-schedules",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
    ),
  update: (id: string, data: Record<string, any>) =>
    apiFetch<{ ok: boolean }>(`/report-schedules/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    apiFetch<{ ok: boolean }>(`/report-schedules/${id}`, { method: "DELETE" }),
  runNow: (id: string) =>
    apiFetch<{ ok: boolean; sent: number; total: number; errors: string[] }>(
      `/report-schedules/${id}/run-now`,
      {
        method: "POST",
      },
    ),
};

export const auditLog = {
  list: (limit = 100, entity?: string, action?: string) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (entity) params.set("entity", entity);
    if (action) params.set("action", action);
    return apiFetch<{ entries: AuditLogEntry[] }>(`/audit-log?${params}`);
  },
};
