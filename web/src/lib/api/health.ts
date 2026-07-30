import { apiFetch, buildPaginationParams } from "./client";

export const health = {
  check: () =>
    apiFetch<{ server: string; stdb: string; module: string }>("/health"),
  ready: () => apiFetch<{ status: string }>("/health/ready"),
};
