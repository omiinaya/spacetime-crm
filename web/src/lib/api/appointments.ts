import { apiFetch, buildPaginationParams } from './client';
import type { Appointment } from './types';

export const appointments = {
  list: (offset?: number, limit?: number) => {
    const p = new URLSearchParams();
    if (offset !== undefined) p.set('offset', String(offset));
    if (limit !== undefined) p.set('limit', String(limit));
    const qs = p.toString();
    return apiFetch<{
      appointments: Appointment[];
      total: number;
      offset: number;
      limit: number;
    }>(`/appointments${qs ? `?${qs}` : ''}`);
  },
  create: (data: Partial<Appointment>) =>
    apiFetch<{ ok: boolean }>('/appointments', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateStatus: (id: string, status: string) =>
    apiFetch<{ ok: boolean }>(`/appointments/${id}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    }),
  delete: (id: string) => apiFetch<{ ok: boolean }>(`/appointments/${id}`, { method: 'DELETE' }),
  recurrence: {
    set: (id: string, rule: string) =>
      apiFetch<{ ok: boolean }>(`/appointments/${id}/recurrence`, {
        method: 'PUT',
        body: JSON.stringify({ recurrence_rule: rule }),
      }),
  },
  generateNext: (seriesId: string) =>
    apiFetch<{
      ok: boolean;
      start_time?: number;
      end_time?: number;
      error?: string;
    }>('/appointments/generate-next', {
      method: 'POST',
      body: JSON.stringify({ series_id: seriesId }),
    }),
  recurring: {
    list: () => apiFetch<{ series: Appointment[] }>('/appointments/recurring'),
  },
  byTech: (start: number, end: number) =>
    apiFetch<{
      groups: {
        user_id: string;
        user_name: string;
        appointments: Appointment[];
      }[];
      unassigned: Appointment[];
    }>(`/appointments/by-tech?start=${start}&end=${end}`),
};
