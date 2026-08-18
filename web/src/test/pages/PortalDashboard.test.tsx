/**
 * Tests for PortalDashboard loading + error states (ROADMAP 6A-1 / 6C-1).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PortalDashboard from "@/pages/PortalDashboard";

const { mockStatsGet } = vi.hoisted(() => ({
  mockStatsGet: vi.fn(),
}));

vi.mock("@/lib/portal-auth", () => ({
  portalApi: { stats: { get: (...args: any[]) => mockStatsGet(...args) } },
  usePortalAuth: () => ({ customer: { first_name: "Ada" } }),
  PortalStats: {},
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockStatsGet.mockResolvedValue({
    total_tickets: 3,
    open_tickets: 1,
    total_invoices: 4,
    total_billed: 500,
    total_paid: 200,
    balance_due: 300,
    upcoming_appointments: 2,
  });
});

describe("PortalDashboard loading state", () => {
  it("shows a loading placeholder while stats are pending", async () => {
    mockStatsGet.mockReturnValue(new Promise(() => {})); // never resolves

    render(<PortalDashboard />);

    // Skeleton placeholders visible while loading
    expect(document.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
    expect(screen.queryByText("Open Tickets")).not.toBeInTheDocument();
  });
});

describe("PortalDashboard error state", () => {
  it("shows an error banner instead of silently swallowing the failure", async () => {
    mockStatsGet.mockRejectedValue(new Error("API 500: boom"));

    render(<PortalDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load your dashboard/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("recovers when Retry succeeds", async () => {
    mockStatsGet
      .mockRejectedValueOnce(new Error("API 500: boom"))
      .mockResolvedValueOnce({
        total_tickets: 3,
        open_tickets: 1,
        total_invoices: 4,
        total_billed: 500,
        total_paid: 200,
        balance_due: 300,
        upcoming_appointments: 2,
      });

    render(<PortalDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load your dashboard/i)).toBeInTheDocument();
    });

    await userEvent.setup().click(screen.getByRole("button", { name: /retry/i }));

    await waitFor(() => {
      expect(screen.getByText("Open Tickets")).toBeInTheDocument();
    });
    expect(screen.queryByText(/failed to load your dashboard/i)).not.toBeInTheDocument();
  });
});

describe("PortalDashboard success state", () => {
  it("renders stats cards when data loads", async () => {
    render(<PortalDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Welcome, Ada!")).toBeInTheDocument();
      expect(screen.getByText("Open Tickets")).toBeInTheDocument();
      expect(screen.getByText("Balance Due")).toBeInTheDocument();
    });

    // Balance due formatted via Intl
    expect(screen.getByText("$300.00")).toBeInTheDocument();
  });
});
