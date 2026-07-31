/**
 * Tests for EstimatesPage — rendering, empty state, create form.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import EstimatesPage from "@/pages/EstimatesPage";
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

const customerAlice = {
	id: "cust_1",
	first_name: "Alice",
	last_name: "Johnson",
	email: "alice@example.com",
	phone: "+15551112222",
	mobile: "",
	company: "Acme",
	balance: 0,
	created_at: Date.now(),
};

const estimate1 = {
	id: "est_1",
	estimate_number: 3001,
	tenant_id: "t1",
	customer_id: "cust_1",
	status: "draft",
	total: 150.0,
	currency: "USD",
	created_at: Date.now() - 3600000,
	updated_at: Date.now() - 3600000,
};

function pushPage(estimates: unknown[], total = estimates.length) {
	mock.push({ estimates, total, offset: 0, limit: 25 }); // estimates
	mock.push({ customers: [customerAlice], total: 1, offset: 0, limit: 25 }); // customers
}

beforeEach(() => {
	mock.reset();
});

afterEach(() => {
	vi.clearAllTimers();
});

describe("EstimatesPage", () => {
	it("renders page header and estimates from API", async () => {
		pushPage([estimate1]);
		render(<EstimatesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Estimates")).toBeTruthy();
			expect(screen.getByText("#3001")).toBeTruthy();
		});
	});

	it("shows empty state when no estimates exist", async () => {
		pushPage([]);
		render(<EstimatesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/no estimates yet/i)).toBeTruthy();
		});
	});

	it("opens the new estimate form", async () => {
		pushPage([]);
		render(<EstimatesPage />, { wrapper });

		await waitFor(() => {
			expect(
				screen.getAllByRole("button", { name: /new estimate/i }).length,
			).toBeGreaterThanOrEqual(1);
		});

		const newBtn = screen.getAllByRole("button", { name: /new estimate/i })[0];
		await userEvent.click(newBtn);

		await waitFor(() => {
			expect(screen.getByText(/select customer/i)).toBeTruthy();
			expect(screen.getByPlaceholderText(/ticket id/i)).toBeTruthy();
		});
	});

	it("filters estimates by status", async () => {
		pushPage([estimate1]);
		render(<EstimatesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("#3001")).toBeTruthy();
		});

		const approvedBtn = screen.getByRole("button", { name: /^approved$/i });
		await userEvent.click(approvedBtn);

		await waitFor(() => {
			const calls = mock.calls();
			expect(
				calls.some(
					(c) =>
						c.url.includes("/estimates") && c.url.includes("status=approved"),
				),
			).toBeTruthy();
		});
	});
});
