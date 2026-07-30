import { apiFetch, buildPaginationParams } from './client';
import type { Product, InventoryAdjustment } from './types';

export const products = {
  list: (
    search?: string,
    category?: string,
    location?: string,
    offset?: number,
    limit?: number,
  ) => {
    const p = new URLSearchParams();
    if (search) p.set('search', search);
    if (category) p.set('category', category);
    if (location) p.set('location', location);
    if (offset !== undefined) p.set('offset', String(offset));
    if (limit !== undefined) p.set('limit', String(limit));
    const qs = p.toString();
    return apiFetch<{
      products: Product[];
      total: number;
      offset: number;
      limit: number;
    }>(`/products${qs ? `?${qs}` : ''}`);
  },
  categories: () => apiFetch<{ categories: string[] }>('/products/categories'),
  locations: () => apiFetch<{ locations: string[] }>('/products/locations'),
  create: (data: Partial<Product>) =>
    apiFetch<{ ok: boolean }>('/products', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateQuantity: (id: string, quantity_on_hand: number) =>
    apiFetch<{ ok: boolean }>(`/products/${id}/quantity`, {
      method: 'PUT',
      body: JSON.stringify({ quantity_on_hand }),
    }),
  delete: (id: string) => apiFetch<{ ok: boolean }>(`/products/${id}`, { method: 'DELETE' }),
  byBarcode: (barcode: string) =>
    apiFetch<{ product: Product }>(`/products/by-barcode/${encodeURIComponent(barcode)}`),
  adjustments: {
    list: (productId: string) =>
      apiFetch<{ adjustments: InventoryAdjustment[] }>(`/products/${productId}/adjustments`),
    create: (productId: string, data: Partial<InventoryAdjustment>) =>
      apiFetch<{ ok: boolean }>(`/products/${productId}/adjustments`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },
  lowStock: {
    list: () => apiFetch<{ products: Product[]; count: number }>('/products/low-stock'),
    notify: () =>
      apiFetch<{ ok: boolean; count?: number; notified?: string }>('/products/low-stock/notify', {
        method: 'POST',
      }),
  },
  transfer: (data: {
    source_product_id: string;
    destination_product_id: string;
    quantity: number;
    reference_id?: string;
    notes?: string;
  }) =>
    apiFetch<{ ok: boolean; quantity: number; reference: string }>('/products/transfer', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};
