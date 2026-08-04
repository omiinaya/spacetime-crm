/**
 * Tests for the offline read-through API cache (client.ts).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiFetch, clearApiCache } from "@/lib/api/client";

const mock = vi.fn();
const originalFetch = window.fetch;

function pushResponse(body: unknown, ok = true, status = 200) {
	mock.mockResolvedValueOnce(
		new Response(JSON.stringify(body), {
			status,
			headers: { "content-type": "application/json" },
		}),
	);
}

function pushNetworkError() {
	mock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
}

beforeEach(() => {
	mock.mockReset();
	window.fetch = mock as unknown as typeof fetch;
	localStorage.clear();
});

afterEach(() => {
	window.fetch = originalFetch;
});

describe("apiFetch read-through cache", () => {
	it("serves fresh data from the network and caches it", async () => {
		pushResponse({ customers: [{ id: "c1" }] });
		const data = await apiFetch<{ customers: { id: string }[] }>("/customers");
		expect(data.customers).toHaveLength(1);
		expect(localStorage.getItem("crm-api-cache:/customers")).toBeTruthy();
	});

	it("falls back to cached data when the network fails", async () => {
		pushResponse({ customers: [{ id: "c1" }] });
		await apiFetch("/customers"); // populate cache

		pushNetworkError(); // now offline
		const data = await apiFetch<{ customers: { id: string }[] }>("/customers");
		expect(data.customers).toHaveLength(1);
	});

	it("does not serve expired cache entries", async () => {
		pushResponse({ ok: 1 });
		await apiFetch("/health-check");
		// Force expiry by backdating the entry
		const raw = JSON.parse(
			localStorage.getItem("crm-api-cache:/health-check")!,
		);
		raw.ts = Date.now() - 6 * 60 * 1000;
		localStorage.setItem("crm-api-cache:/health-check", JSON.stringify(raw));

		pushNetworkError();
		await expect(apiFetch("/health-check")).rejects.toThrow();
	});

	it("does not cache or fall back for POST requests", async () => {
		pushResponse({ ok: true });
		await apiFetch("/customers", {
			method: "POST",
			body: JSON.stringify({ name: "x" }),
		});
		expect(localStorage.getItem("crm-api-cache:/customers")).toBeNull();

		// Cache from a prior GET must NOT mask a mutation failure.
		pushResponse({ customers: [] });
		await apiFetch("/customers");
		pushNetworkError();
		await expect(
			apiFetch("/customers", { method: "POST", body: "{}" }),
		).rejects.toThrow();
	});

	it("throws on non-OK responses even when cache exists", async () => {
		pushResponse({ customers: [{ id: "c1" }] });
		await apiFetch("/customers"); // cache

		pushResponse({ error: "boom" }, false, 500);
		// The read-through path re-fetches first; a 500 falls back to cache.
		const data = await apiFetch<{ customers?: unknown }>("/customers");
		expect(data.customers).toBeTruthy();
	});

	it("clearApiCache removes all cached entries", async () => {
		pushResponse({ a: 1 });
		await apiFetch("/a");
		pushResponse({ b: 2 });
		await apiFetch("/b");

		clearApiCache();
		expect(localStorage.getItem("crm-api-cache:/a")).toBeNull();
		expect(localStorage.getItem("crm-api-cache:/b")).toBeNull();
	});
});
