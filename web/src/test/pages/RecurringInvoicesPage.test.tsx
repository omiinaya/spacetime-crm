/**
 * Tests for RecurringInvoicesPage — rule list, create form, generate action,
 * pause/resume toggle, and edit.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RecurringInvoicesPage from "@/pages/RecurringInvoicesPage";
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

const rules = [
	{
		id: "rr_1",
		tenant_id: "t_1",
		customer_id: "cust_1",
		name: "Monthly Cleaning",
		frequency: "monthly",
		interval_count: 1,
		next_generation_date: 1750000000000,
		last_generated_date: 1740000000000,
		due_date_days: 30,
		line_items_json:
			'[{"description":"Deep Clean","quantity":1,"unit_price":150,"item_type":"service"}]',
		status: "active",
		created_at: 1700000000000,
		updated_at: 1700000000000,
		customer_name: "Alice Smith",
	},
	{
		id: "rr_2",
		tenant_id: "t_1",
		customer_id: "cust_2",
		name: "Server Maintenance",
		frequency: "weekly",
		interval_count: 1,
		next_generation_date: 1750000000000,
		last_generated_date: 0,
		due_date_days: 14,
		line_items_json: "[]",
		status: "paused",
		created_at: 1700000000000,
		updated_at: 1700000000000,
		customer_name: "Bob Jones",
	},
];

const customers = [
	{ id: "cust_1", name: "Alice Smith", email: "alice@test.com" },
	{ id: "cust_2", name: "Bob Jones", email: "bob@test.com" },
];

function pushPage() {
	mock.push({ rules }); // /api/recurring-invoices
	mock.push({ customers, total: 2 }); // /api/customers
}

beforeEach(() => {
	mock.reset();
});

describe("RecurringInvoicesPage", () => {
	it("renders page header and rule list", async () => {
		pushPage();
		render(<RecurringInvoicesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Monthly Cleaning")).toBeTruthy();
		});
		expect(screen.getByText("Server Maintenance")).toBeTruthy();
		expect(screen.getByText("Alice Smith")).toBeTruthy();
		expect(screen.getByText("Bob Jones")).toBeTruthy();
	});

	it("shows status badges for active and paused", async () => {
		pushPage();
		render(<RecurringInvoicesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Active")).toBeTruthy();
		});
		expect(screen.getByText("Paused")).toBeTruthy();
	});

	it("opens create form on New Rule click", async () => {
		pushPage();
		render(<RecurringInvoicesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Recurring Invoices")).toBeTruthy();
		});

		await userEvent.click(screen.getByText("New Rule"));
		await waitFor(() => {
			expect(screen.getByText("Create Recurring Invoice Rule")).toBeTruthy();
		});
	});

	it("creates a rule from the form", async () => {
		pushPage();
		mock.push({ ok: true }); // POST /api/recurring-invoices
		render(<RecurringInvoicesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Recurring Invoices")).toBeTruthy();
		});

		await userEvent.click(screen.getByText("New Rule"));
		await waitFor(() => {
			expect(
				screen.getByPlaceholderText("e.g. Monthly Maintenance"),
			).toBeTruthy();
		});

		await userEvent.type(
			screen.getByPlaceholderText("e.g. Monthly Maintenance"),
			"Oil Change",
		);
		await userEvent.click(screen.getByText("Create Rule"));

		await waitFor(() => {
			expect(mock.calls().some((c) => c.init?.method === "POST")).toBe(true);
		});
	});

	it("pauses an active rule via toggle button", async () => {
		pushPage();
		mock.push({ ok: true }); // PUT /api/recurring-invoices/rr_1
		render(<RecurringInvoicesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Monthly Cleaning")).toBeTruthy();
		});

		await userEvent.click(screen.getByTitle("Pause"));

		await waitFor(() => {
			expect(mock.calls().some((c) => c.init?.method === "PUT")).toBe(true);
		});
	});

	it("triggers generate action", async () => {
		pushPage();
		mock.push({ ok: true }); // POST /api/recurring-invoices/generate
		render(<RecurringInvoicesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Recurring Invoices")).toBeTruthy();
		});

		await userEvent.click(screen.getByText("Generate Now"));

		await waitFor(() => {
			expect(
				mock
					.calls()
					.some(
						(c) =>
							c.url.includes("/recurring-invoices/generate") &&
							c.init?.method === "POST",
					),
			).toBe(true);
		});
	});

	it("shows empty state when no rules", async () => {
		mock.push({ rules: [] });
		mock.push({ customers, total: 2 });
		render(<RecurringInvoicesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/no recurring/i)).toBeTruthy();
		});
	});

	it("opens edit form populated with rule data", async () => {
		pushPage();
		render(<RecurringInvoicesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Monthly Cleaning")).toBeTruthy();
		});

		await userEvent.click(screen.getAllByTitle("Edit")[0]);

		await waitFor(() => {
			expect(screen.getByText("Edit Rule")).toBeTruthy();
		});
		expect(screen.getByDisplayValue("Monthly Cleaning")).toBeTruthy();
	});
});
