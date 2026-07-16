/**
 * Smoke test for DashboardPage - renders with stats and navigation
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "../test-utils";
import DashboardPage from "@/pages/DashboardPage";

vi.mock("@tanstack/react-query", async (importOriginal) => {
	const actual = await importOriginal();
	return {
		...actual,
		useMutation: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
	};
});

const defaultStats = {
	total_customers: 42,
	total_tickets: 10,
	open_tickets: 7,
	revenue: 15000,
	pending_revenue: 3000,
	upcoming_appointments: 3,
	monthly_revenue: 5000,
	revenue_target: 10000,
	avg_resolution_hours: 24,
	my_ticket_counts: { all: 5, urgent: 1, high: 2, medium: 1, low: 1 },
	my_tickets: [],
	today_appointments: [],
	overdue_invoices: [],
	overdue_invoices_count: 0,
	overdue_invoices_total: 0,
};

describe("DashboardPage", () => {
	it("renders basic stats in cards", () => {
		render(<DashboardPage stats={defaultStats} onNavigate={vi.fn()} />);
		expect(screen.getByText("42")).toBeInTheDocument();
		expect(screen.getByText("7")).toBeInTheDocument();
		expect(screen.getByText("3")).toBeInTheDocument();
	});
});
