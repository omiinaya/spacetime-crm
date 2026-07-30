import { apiFetch, buildPaginationParams } from './client';
import type { Tenant, TenantMember } from './types';

export const tenants = {
  list: () => apiFetch<{ tenants: Tenant[] }>('/tenants'),
  get: (id: string) => apiFetch<{ tenant: Tenant }>(`/tenants/${id}`),
  create: (data: { name: string; slug?: string }) =>
    apiFetch<{ ok: boolean }>('/tenants', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  update: (
    id: string,
    data: {
      name?: string;
      slug?: string;
      logo_url?: string;
      settings?: string;
    },
  ) =>
    apiFetch<{ ok: boolean }>(`/tenants/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  delete: (id: string) => apiFetch<{ ok: boolean }>(`/tenants/${id}`, { method: 'DELETE' }),
  addMember: (tenantId: string, data: { username: string; role: string }) =>
    apiFetch<{ ok: boolean }>(`/tenants/${tenantId}/members`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  removeMember: (tenantId: string, memberId: string) =>
    apiFetch<{ ok: boolean }>(`/tenants/${tenantId}/members/${memberId}`, {
      method: 'DELETE',
    }),
  updateMemberRole: (tenantId: string, memberId: string, role: string) =>
    apiFetch<{ ok: boolean }>(`/tenants/${tenantId}/members/${memberId}`, {
      method: 'PUT',
      body: JSON.stringify({ role }),
    }),
  migrate: (data: { name?: string; slug?: string }) =>
    apiFetch<{
      ok: boolean;
      tenant_id?: string;
      users_migrated?: number;
      tables_updated?: Record<string, boolean>;
    }>('/tenants/migrate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};
