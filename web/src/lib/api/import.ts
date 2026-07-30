import { apiFetch, API_BASE } from "./client";

export const import_ = {
  customers: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return fetch(`${API_BASE}/import/customers`, {
      method: "POST",
      body: form,
    }).then((r) => r.json()) as Promise<{
      imported: number;
      errors: string[];
      file: string;
    }>;
  },
  products: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return fetch(`${API_BASE}/import/products`, {
      method: "POST",
      body: form,
    }).then((r) => r.json()) as Promise<{
      imported: number;
      errors: string[];
      file: string;
    }>;
  },
};
