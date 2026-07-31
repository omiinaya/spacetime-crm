import { apiFetch } from "./client";
import type { DashboardStats } from "./types";

export const stats = {
	get: () => apiFetch<DashboardStats>("/stats"),
};
