import { apiFetch, buildPaginationParams } from './client';
import type { WebhookSubscription } from './types';

export const webhooks = {
  list: () => apiFetch<{ subscriptions: WebhookSubscription[] }>('/webhook-subscriptions'),
  create: (data: { url: string; events: string; secret?: string }) =>
    apiFetch<{ ok: boolean }>('/webhook-subscriptions', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  update: (id: string, data: { url: string; events?: string; secret?: string; active?: boolean }) =>
    apiFetch<{ ok: boolean }>(`/webhook-subscriptions/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    apiFetch<{ ok: boolean }>(`/webhook-subscriptions/${id}`, {
      method: 'DELETE',
    }),
  test: (id: string) =>
    apiFetch<{ ok: boolean; status_code?: number; error?: string }>(
      `/webhook-subscriptions/${id}/test`,
      { method: 'POST' },
    ),
};
