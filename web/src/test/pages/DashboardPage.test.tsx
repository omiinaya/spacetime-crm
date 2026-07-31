/**
 * Tests for DashboardPage — summary cards, revenue target bar, overdue alert,
 * quick actions, and navigation callbacks.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DashboardPage from "@/pages/DashboardPage";
import type { DashboardStats } from "@/lib/api/types";
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

const stats: DashboardStats = {
	total_customers: 42,
	total_tickets: 15,
	open_tickets: 3,
	revenue: 1234.5,
	pending_revenue: 200,
	upcoming_appointments: 5,
	monthly_revenue: 800,
	revenue_target: 1000,
	avg_resolution_hours: 6.5,
	overdue_invoices_count: 2,
	overdue_invoices_total: 345.67,
	overdue_invoices: [
		{
			id: "inv_111",
			invoice_number: "INV-1001",
			total: 150.25,
			due_date: "2026-07-01",
			customer_id: "cust_1",
			status: "sent",
			currency: "USD",
		},
		{
			id: "inv_222",
			invoice_number: "INV-1002",
			total: 195.42,
			due_date: "2026-07-02",
			customer_id: "cust_2",
			status: "sent",
			currency: "USD",
		},
	] as any,
	my_ticket_counts: { all: 4, urgent: 1, high: 2, medium: 1, low: 0 },
	invoice_item_type_breakdown: [
		{ item_type: "service", count: 3, total: 300 },
		{ item_type: "part", count: 2, total: 100 },
	],
	estimate_item_type_breakdown: [],
};

const reportsData = {
	revenue_by_month: [{ month: "Jan 26", revenue: 1200 }],
	ticket_by_status: [{ status: "new", count: 3 }],
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

beforeEach(() => {
	mock.reset();
});

describe("DashboardPage", () => {
	it("renders summary cards with stats values", async () => {
		mock.push(reportsData);
		render(<DashboardPage stats={stats} onNavigate={vi.fn()} />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Total Customers")).toBeTruthy();
		});
		expect(screen.getByText("42")).toBeTruthy();
		expect(screen.getByText("Open Tickets")).toBeTruthy();
		expect(screen.getByText("3")).toBeTruthy();
		expect(screen.getByText("$1234.50")).toBeTruthy();
		expect(screen.getByText("Upcoming Appointments")).toBeTruthy();
		expect(screen.getByText("5")).toBeTruthy();
		expect(screen.getByText("6.5h")).toBeTruthy();
	});

	it("renders zero defaults when stats are null", async () => {
		mock.push(reportsData);
		render(<DashboardPage stats={null} onNavigate={vi.fn()} />, {
			wrapper,
		});

		await waitFor(() => {
			expect(screen.getByText("Total Customers")).toBeTruthy();
		});
		expect(screen.getByText("$0.00")).toBeTruthy();
		// Avg resolution card only renders when stats exist
		expect(screen.queryByText("Avg Resolution")).toBeNull();
	});

	it("renders revenue target progress and percent", async () => {
		mock.push(reportsData);
		render(<DashboardPage stats={stats} onNavigate={vi.fn()} />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Monthly Revenue Target")).toBeTruthy();
		});
		expect(
			screen.getAllByText((_, node) => {
				const text = node?.textContent ?? "";
				return (
					node?.children.length === 0 &&
					text.includes("800.00 / $") &&
					text.includes("1000.00")
				);
			}).length,
		).toBeGreaterThan(0);
		expect(screen.getByText("80% of monthly target")).toBeTruthy();
	});

	it("shows 0% when target is zero (no divide-by-zero crash)", async () => {
		mock.push(reportsData);
		render(
			<DashboardPage
				stats={{ ...stats, revenue_target: 0, monthly_revenue: 500 }}
				onNavigate={vi.fn()}
			/>,
			{ wrapper },
		);

		await waitFor(() => {
			expect(screen.getByText("0% of monthly target")).toBeTruthy();
		});
	});

	it("renders overdue invoice alert with count and total", async () => {
		mock.push(reportsData);
		render(<DashboardPage stats={stats} onNavigate={vi.fn()} />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("2 Overdue Invoices")).toBeTruthy();
		});
		expect(screen.getByText(/345\.67/)).toBeTruthy();
		expect(screen.getByText("#INV-1001")).toBeTruthy();
		expect(screen.getByText("#INV-1002")).toBeTruthy();
	});

	it("does not render overdue alert when none overdue", async () => {
		mock.push(reportsData);
		render(
			<DashboardPage
				stats={{ ...stats, overdue_invoices_count: 0 }}
				onNavigate={vi.fn()}
			/>,
			{ wrapper },
		);

		await waitFor(() => {
			expect(screen.getByText("Total Customers")).toBeTruthy();
		});
		expect(screen.queryByText(/Overdue Invoice/)).toBeNull();
	});

	it("navigates when summary card and quick action clicked", async () => {
		mock.push(reportsData);
		const onNavigate = vi.fn();
		render(<DashboardPage stats={stats} onNavigate={onNavigate} />, {
			wrapper,
		});

		await waitFor(() => {
			expect(screen.getByText("Total Customers")).toBeTruthy();
		});
		await userEvent.click(screen.getByText("Total Customers"));
		expect(onNavigate).toHaveBeenCalledWith("customers");

		await userEvent.click(screen.getByText("New Ticket"));
		expect(onNavigate).toHaveBeenCalledWith("tickets");
	});

	it("renders quick actions", async () => {
		mock.push(reportsData);
		render(<DashboardPage stats={stats} onNavigate={vi.fn()} />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Quick Actions")).toBeTruthy();
		});
		for (const label of [
			"New Customer",
			"New Ticket",
			"New Invoice",
			"New Appointment",
			"Add Product",
		]) {
			expect(screen.getByText(label)).toBeTruthy();
		}
	});

	it("shows 'No revenue data yet' when reports empty", async () => {
		mock.push({
			revenue_by_month: [],
			ticket_by_status: [],
			invoice_by_status: [],
			appt_by_month: [],
			totals: {},
			resolution_times: [],
		});
		render(<DashboardPage stats={stats} onNavigate={vi.fn()} />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("No revenue data yet")).toBeTruthy();
		});
		expect(screen.getByText("No ticket data yet")).toBeTruthy();
	});

	it("shows urgent ticket badge from my_ticket_counts", async () => {
		mock.push(reportsData);
		render(<DashboardPage stats={stats} onNavigate={vi.fn()} />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("My Tickets")).toBeTruthy();
		});
		expect(screen.getByText("1 urgent")).toBeTruthy();
		expect(screen.getByText("2 high")).toBeTruthy();
	});
});
