/**
 * Tests for PaymentMethodsPage — list, brand/last4 display, default badge,
 * set-default and delete actions.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PaymentMethodsPage from "@/pages/PaymentMethodsPage";
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

const methods = [
	{
		id: "pm_1",
		customer_id: "cust_1",
		stripe_payment_method_id: "pm_stripe_1",
		brand: "visa",
		last4: "4242",
		last_4: "4242",
		exp_month: 12,
		exp_year: 2027,
		is_default: true,
		created_at: 1700000000000,
		customer_name: "Alice Smith",
	},
	{
		id: "pm_2",
		customer_id: "cust_2",
		stripe_payment_method_id: "pm_stripe_2",
		brand: "mastercard",
		last4: "5555",
		last_4: "5555",
		exp_month: 6,
		exp_year: 2026,
		is_default: false,
		created_at: 1700000000000,
		customer_name: "Bob Jones",
	},
];

const customers = [
	{
		id: "cust_1",
		first_name: "Alice",
		last_name: "Smith",
		email: "alice@test.com",
	},
	{
		id: "cust_2",
		first_name: "Bob",
		last_name: "Jones",
		email: "bob@test.com",
	},
];

function pushPage() {
	mock.push({ payment_methods: methods, total: 2 }); // /api/payment-methods
	mock.push({ customers, total: 2 }); // /api/customers
}

beforeEach(() => {
	mock.reset();
});

describe("PaymentMethodsPage", () => {
	it("renders page header and payment methods", async () => {
		pushPage();
		render(<PaymentMethodsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Payment Methods")).toBeTruthy();
		});
		await waitFor(() => {
			expect(screen.getByText("Alice Smith")).toBeTruthy();
		});
		expect(screen.getByText("Bob Jones")).toBeTruthy();
	});

	it("shows card brand and last4", async () => {
		pushPage();
		render(<PaymentMethodsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/visa/)).toBeTruthy();
		});
		expect(screen.getByText(/4242/)).toBeTruthy();
		expect(screen.getByText(/mastercard/)).toBeTruthy();
		expect(screen.getByText(/5555/)).toBeTruthy();
	});

	it("marks the default method with a badge", async () => {
		pushPage();
		render(<PaymentMethodsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Alice Smith")).toBeTruthy();
		});
		expect(screen.getByText(/default/i)).toBeTruthy();
	});

	it("sets a method as default", async () => {
		pushPage();
		mock.push({ ok: true }); // PUT /api/payment-methods/pm_2/default
		render(<PaymentMethodsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Bob Jones")).toBeTruthy();
		});

		await userEvent.click(screen.getByTitle("Set as default"));

		await waitFor(() => {
			expect(mock.calls().some((c) => c.init?.method === "PUT")).toBe(true);
		});
	});

	it("deletes a payment method", async () => {
		vi.spyOn(window, "confirm").mockReturnValue(true);
		pushPage();
		mock.push({ ok: true }); // DELETE /api/payment-methods/pm_1
		render(<PaymentMethodsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Alice Smith")).toBeTruthy();
		});

		const buttons = screen.getAllByRole("button");
		// Last button is the trash of the second row.
		await userEvent.click(buttons[buttons.length - 1]);

		await waitFor(() => {
			expect(mock.calls().some((c) => c.init?.method === "DELETE")).toBe(true);
		});
	});

	it("shows empty state when no methods", async () => {
		mock.push({ payment_methods: [], total: 0 });
		mock.push({ customers, total: 2 });
		render(<PaymentMethodsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("No saved payment methods")).toBeTruthy();
		});
	});
});
