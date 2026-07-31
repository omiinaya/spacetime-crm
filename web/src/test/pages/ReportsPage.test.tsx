/**
 * Tests for ReportsPage — rendering, revenue data, scheduled report form.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ReportsPage from "@/pages/ReportsPage";
import { mockFetch } from "../lib/mock-fetch";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { AuthProvider } from "@/lib/auth";

const wrapper = ({ children }: { children: React.ReactNode }) => {
	const qc = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	return (
		<AuthProvider>
			<QueryClientProvider client={qc}>
				<Toaster />
				{children}
			</QueryClientProvider>
		</AuthProvider>
	);
};

const mock = mockFetch();

const reportsData = {
	revenue_by_month: [
		{ month: "Jan 26", revenue: 1200 },
		{ month: "Feb 26", revenue: 2400 },
	],
	ticket_by_status: [
		{ status: "new", count: 3 },
		{ status: "resolved", count: 10 },
	],
	invoice_by_status: [{ status: "paid", count: 5 }],
	appt_by_month: [],
	totals: {
		total_revenue: 3600,
		total_tickets: 13,
		open_tickets: 3,
		total_sent: 5,
		total_paid: 5,
		outstanding_revenue: 0,
		avg_resolution_hours: 0,
		sla_breach_rate: 0,
		sla_breach_count: 0,
		overdue_invoice_rate: 0,
		overdue_invoice_count: 0,
	},
	resolution_times: [],
};

function pushPage() {
	mock.push(reportsData); // /api/reports
	mock.push({ schedules: [] }); // /api/report-schedules
}

beforeEach(() => {
	mock.reset();
});

afterEach(() => {
	vi.clearAllTimers();
});

describe("ReportsPage", () => {
	it("renders page header", async () => {
		pushPage();
		render(<ReportsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Reports")).toBeTruthy();
		});
	});

	it("renders revenue summary from API", async () => {
		pushPage();
		render(<ReportsPage />, { wrapper });

		// Recharts charts don't render axis ticks in jsdom, so assert on the
		// summary cards that render API totals directly.
		await waitFor(() => {
			expect(screen.getByText("Total Revenue")).toBeTruthy();
			expect(screen.getByText("$3600.00")).toBeTruthy(); // totals.total_revenue
		});
	});

	it("shows schedule report form", async () => {
		pushPage();
		render(<ReportsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Reports")).toBeTruthy();
		});

		const scheduleBtn = screen.getByRole("button", { name: /new schedule/i });
		await userEvent.click(scheduleBtn);

		await waitFor(() => {
			expect(
				screen.getByPlaceholderText(/weekly revenue report/i),
			).toBeTruthy();
		});
	});

	it("handles partial reports data without crashing", async () => {
		// Regression: page crashed with 'Cannot read properties of undefined
		// (reading length)' when the API response was missing breakdown arrays.
		mock.push({ totals: {} }); // partial response
		mock.push({ schedules: [] });
		render(<ReportsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Reports")).toBeTruthy();
		});
	});
});
