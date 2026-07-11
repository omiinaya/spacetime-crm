// ── API Types, interfaces, and constants ──
// Extracted from api.ts for modularity

export interface PaginationParams {
  offset?: number;
  limit?: number;
}

export interface PaginatedResponse<T> {
  total: number;
  offset: number;
  limit: number;
  [key: string]: T[] | number;
}

export interface Customer {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  zip?: string;
  notes?: string;
  created_at: number;
  updated_at: number;
  deleted_at?: number;
  tenant_id: string;
  longtitude?: number;
  latitude?: number;
  geo_updated_at?: number;
}
