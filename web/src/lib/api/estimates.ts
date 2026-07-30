import { apiFetch, buildPaginationParams } from './client';
import type { Estimate, EstimateLineItem } from './types';

export const estimates = {
  list: (status?: string, offset?: number, limit?: number) => {
    const p = new URLSearchParams();
    if (status) p.set('status', status);
    if (offset !== undefined) p.set('offset', String(offset));
    if (limit !== undefined) p.set('limit', String(limit));
    const qs = p.toString();
    return apiFetch<{
      estimates: Estimate[];
      total: number;
      offset: number;
      limit: number;
    }>(`/estimates${qs ? `?${qs}` : ''}`);
  },
  create: (data: Partial<Estimate>) =>
    apiFetch<{ ok: boolean }>('/estimates', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateStatus: (id: string, status: string) =>
    apiFetch<{ ok: boolean }>(`/estimates/${id}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    }),
  lineItems: {
    list: (estimateId: string) =>
      apiFetch<{ line_items: EstimateLineItem[] }>(`/estimates/${estimateId}/line-items`),
    create: (estimateId: string, data: Partial<EstimateLineItem>) =>
      apiFetch<{ ok: boolean }>(`/estimates/${estimateId}/line-items`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
  convert: (id: string) =>
    apiFetch<{ ok: boolean }>(`/estimates/${id}/convert`, { method: 'POST' }),
  delete: (id: string) => apiFetch<{ ok: boolean }>(`/estimates/${id}`, { method: 'DELETE' }),
};
