import { apiFetch, buildPaginationParams } from "./client";
import type { CustomFieldDefinition, CustomFieldValue } from "./types";

export const customFields = {
  definitions: {
    list: (entityType?: string) =>
      apiFetch<{ definitions: CustomFieldDefinition[] }>(
        `/custom-field-definitions${entityType ? `?entity_type=${entityType}` : ""}`,
      ),
    create: (data: {
      entity_type: string;
      label: string;
      field_type: string;
      options?: string[];
      sort_order?: number;
      required?: boolean;
      active?: boolean;
    }) =>
      apiFetch<{ ok: boolean; id: string }>("/custom-field-definitions", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (
      id: string,
      data: {
        label: string;
        field_type: string;
        options?: string[];
        sort_order?: number;
        required?: boolean;
        active?: boolean;
      },
    ) =>
      apiFetch<{ ok: boolean }>(`/custom-field-definitions/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      apiFetch<{ ok: boolean }>(`/custom-field-definitions/${id}`, {
        method: "DELETE",
      }),
  },
  values: {
    get: (entityId: string) =>
      apiFetch<{ values: CustomFieldValue[] }>(
        `/custom-field-values/${entityId}`,
      ),
    set: (entityId: string, values: Record<string, string>) =>
      apiFetch<{ ok: boolean; count: number }>(
        `/custom-field-values/${entityId}`,
        {
          method: "PUT",
          body: JSON.stringify({ values }),
        },
      ),
  },
};
