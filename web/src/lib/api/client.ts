const API_BASE = "/api";

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
  return res.json();
}

export { apiFetch, buildPaginationParams, getApiToken, API_BASE };
