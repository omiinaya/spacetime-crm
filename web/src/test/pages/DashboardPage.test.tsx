/**
 * Smoke test for DashboardPage - renders with stats and navigation
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import DashboardPage from "@/pages/DashboardPage";
import { renderWithQuery } from "../utils";

vi.mock("@/lib/api", () => ({
	api: {
		appointments: { updateStatus: vi.fn() },
		tickets: { assign: vi.fn() },
		payments: { record: vi.fn() },
		reports: {
			get: vi.fn().mockResolvedValue({
				monthly_revenue: 0,
				ticket_by_status: [],
				invoice_by_status: [],
				top_customers: [],
				recent_tickets: [],
			}),
		},
	},
}));

const defaultStats = {
	total_customers: 42,
	total_tickets: 10,
	open_tickets: 7,
	revenue: 15000,
	pending_revenue: 500,
	upcoming_appointments: 3,
	monthly_revenue: 12000,
	revenue_target: 20000,
	avg_resolution_hours: 4,
};

describe("DashboardPage", () => {
	it("renders basic stats in cards", () => {
		renderWithQuery(
			<DashboardPage stats={defaultStats} onNavigate={vi.fn()} />,
		);
		expect(screen.getByText("42")).toBeInTheDocument();
		expect(screen.getByText("7")).toBeInTheDocument();
		expect(screen.getByText("3")).toBeInTheDocument();
		expect(screen.getByText("$15000.00")).toBeInTheDocument();
	});
});
