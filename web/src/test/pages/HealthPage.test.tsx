/**
 * Tests for HealthPage – loading state, data rendering, error handling,
 * and the 30-second auto-refresh interval.
 *
 * HealthPage fires TWO concurrent fetch calls on mount:
 *   1. GET /api/health       → { server, stdb, module }
 *   2. GET /api/health/ready → { status }
 * Each test must push() responses in this order.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import HealthPage from "@/pages/HealthPage";
import { mockFetch, flushMicrotasks } from "../lib/mock-fetch";

const mock = mockFetch();

beforeEach(() => {
  mock.reset();
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
});

// ── Loading state ──

it("shows 'Checking…' placeholders while data loads", () => {
  mock.push({ server: "ok", stdb: "ok", module: "ok" });
  mock.push({ status: "ok" });
  render(<HealthPage />);

  // Three "Checking..." texts, one per card (server, STDB, module)
  const checking = screen.getAllByText("Checking...");
  expect(checking.length).toBeGreaterThanOrEqual(3);
});

// ── Data rendering ──

it("renders health data when API responds", async () => {
  mock.push({ server: "ok", stdb: "ok", module: "ok" });
  mock.push({ status: "ok" });
  render(<HealthPage />);

  // Wait for the first card badge to appear (multiple "ok" badges exist)
  await waitFor(() => {
    expect(screen.getAllByText("ok").length).toBeGreaterThan(0);
  }, { timeout: 3000 });

  // Both health endpoints were called
  const calls = mock.calls();
  expect(calls.some((c) => c.url.includes("/api/health"))).toBe(true);
  expect(calls.some((c) => c.url.includes("/api/health/ready"))).toBe(true);
});

it("shows error card when API fails", async () => {
  mock.pushFail(500);
  mock.pushFail(500);
  render(<HealthPage />);

  await waitFor(() => {
    // apiFetch throws "API 500: ...", HealthPage shows the error message
    expect(screen.getByText(/API 500/i)).toBeInTheDocument();
  }, { timeout: 3000 });
});

it("shows unknown status when fields are missing", async () => {
  mock.push({}); // empty health response
  mock.push({ status: "ok" });
  render(<HealthPage />);

  const unknowns = await waitFor(() => screen.findAllByText("unknown"), { timeout: 3000 });
  expect(unknowns.length).toBeGreaterThanOrEqual(1);
});

// ── Ready probe ──

it("renders readiness probe when ready data arrives", async () => {
  mock.push({ server: "ok", stdb: "ok", module: "ok" });
  mock.push({ status: "ok" });
  render(<HealthPage />);

  await waitFor(() => {
    expect(screen.getByText(/All systems operational/i)).toBeInTheDocument();
  }, { timeout: 3000 });
});

it("shows degraded message when readiness fails", async () => {
  mock.push({ server: "ok", stdb: "ok", module: "ok" });
  mock.push({ status: "unavailable" });
  render(<HealthPage />);

  await waitFor(() => {
    expect(screen.getByText(/STDB is not reachable/i)).toBeInTheDocument();
  }, { timeout: 3000 });
});

// ── Refresh button ──

it("re-fetches when Refresh button is clicked", async () => {
  mock.push({ server: "ok", stdb: "ok", module: "ok" });
  mock.push({ status: "ok" });
  render(<HealthPage />);

  await waitFor(() => {
    expect(screen.getAllByText("ok").length).toBeGreaterThan(0);
  }, { timeout: 3000 });
  const initialCount = mock.calls().length;

  // Refresh again – push two more responses
  mock.push({ server: "ok", stdb: "ok", module: "ok" });
  mock.push({ status: "ok" });
  const btn = screen.getByRole("button", { name: /refresh/i });
  btn.click();

  await flushMicrotasks();
  expect(mock.calls().length).toBeGreaterThan(initialCount);
});

// ── Auto-refresh interval ──

it("auto-refreshes every 30 seconds", async () => {
  vi.useFakeTimers();

  mock.push({ server: "ok", stdb: "ok", module: "ok" });
  mock.push({ status: "ok" });
  render(<HealthPage />);

  // Wait for initial mount state updates
  await vi.advanceTimersByTimeAsync(0);
  const afterMount = mock.calls().length;
  expect(afterMount).toBe(2);

  // Advance 30 seconds – should trigger another fetch (needs 2 more in queue)
  mock.push({ server: "ok", stdb: "ok", module: "ok" });
  mock.push({ status: "ok" });
  await vi.advanceTimersByTimeAsync(30000);

  expect(mock.calls().length).toBeGreaterThan(afterMount);
});
