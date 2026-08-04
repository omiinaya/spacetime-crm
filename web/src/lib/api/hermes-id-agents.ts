import { apiFetch } from "./client";

/** A hermes-id agent as reported by the auth server admin API. */
export interface HermesIdAgent {
	did: string;
	status: string;
	display_name: string;
	registered_at: string;
	updated_at?: string;
	approved_at?: string | null;
	metadata?: Record<string, unknown>;
	projects?: string[];
}

/** Response shape of GET /agents?project=...&status=... */
export interface HermesIdAgentListResponse {
	agents: HermesIdAgent[];
	total: number;
	page: number;
	page_size: number;
	pages: number;
}

export interface HermesIdAgentActionResult {
	ok?: boolean;
	detail?: string;
}

export const hermesIdAgents = {
	/** List agents for this project (default: pending). */
	list: (status = "pending") =>
		apiFetch<HermesIdAgentListResponse>(
			`/admin/hermes-id/agents?status=${encodeURIComponent(status)}`,
		),
	/** Approve an agent's request for this project. */
	approve: (did: string) =>
		apiFetch<HermesIdAgentActionResult>(
			`/admin/hermes-id/agents/${encodeURIComponent(did)}/approve`,
			{ method: "POST" },
		),
	/** Deny an agent's request for this project. */
	deny: (did: string) =>
		apiFetch<HermesIdAgentActionResult>(
			`/admin/hermes-id/agents/${encodeURIComponent(did)}/deny`,
			{
				method: "POST",
			},
		),
};
