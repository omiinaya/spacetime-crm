const API_BASE = "/api";

/** In-memory GET cache with localStorage persistence (offline read-through). */
const CACHE_PREFIX = "crm-api-cache:";
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

interface CacheEntry {
	body: unknown;
	ts: number;
}

function cacheGet(path: string): unknown | undefined {
	try {
		const raw = localStorage.getItem(CACHE_PREFIX + path);
		if (!raw) return undefined;
		const entry: CacheEntry = JSON.parse(raw);
		if (Date.now() - entry.ts > CACHE_TTL_MS) return undefined;
		return entry.body;
	} catch {
		return undefined;
	}
}

function cacheSet(path: string, body: unknown): void {
	try {
		const entry: CacheEntry = { body, ts: Date.now() };
		localStorage.setItem(CACHE_PREFIX + path, JSON.stringify(entry));
	} catch {
		// Storage full / unavailable — cache is best-effort
	}
}

/** Clear the API response cache (e.g. after a mutation or logout). */
export function clearApiCache(): void {
	try {
		const keys: string[] = [];
		for (let i = 0; i < localStorage.length; i++) {
			const k = localStorage.key(i);
			if (k && k.startsWith(CACHE_PREFIX)) keys.push(k);
		}
		for (const k of keys) localStorage.removeItem(k);
	} catch {
		// ignore
	}
}

function buildPaginationParams(offset?: number, limit?: number): string {
	if (offset === undefined && limit === undefined) return "";
	const p = new URLSearchParams();
	if (offset !== undefined) p.set("offset", String(offset));
	if (limit !== undefined) p.set("limit", String(limit));
	return "?" + p.toString();
}

function getApiToken(): string | null {
	try {
		return localStorage.getItem("crm_token");
	} catch {
		return null;
	}
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
	const token = getApiToken();
	const authHeader: Record<string, string> = token
		? { Authorization: `Bearer ${token}` }
		: {};
	const method = options?.method ?? "GET";
	const cacheable = method === "GET";

	// Read-through cache: on network failure, serve the last known good body.
	if (cacheable) {
		const cached = cacheGet(path);
		if (cached !== undefined) {
			try {
				const res = await fetch(`${API_BASE}${path}`, {
					headers: {
						"Content-Type": "application/json",
						...authHeader,
						...options?.headers,
					},
					...options,
				});
				if (res.ok) {
					const body = await res.json();
					cacheSet(path, body);
					return body;
				}
				throw new Error(`API ${res.status}`);
			} catch {
				return cached as T;
			}
		}
	}

	const res = await fetch(`${API_BASE}${path}`, {
		headers: {
			"Content-Type": "application/json",
			...authHeader,
			...options?.headers,
		},
		...options,
	});
	if (!res.ok) {
		const text = await res.text().catch(() => "Unknown error");
		throw new Error(`API ${res.status}: ${text.slice(0, 200)}`);
	}
	const body = await res.json();
	if (cacheable) cacheSet(path, body);
	return body;
}

export { apiFetch, buildPaginationParams, getApiToken, API_BASE };
