/**
 * Tests for PortalInvoicesPage — invoice list, expand detail, record payment,
 * and Stripe checkout initiation.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PortalInvoicesPage from "@/pages/PortalInvoicesPage";
import { PortalAuthProvider } from "@/lib/portal-auth";
import { mockFetch } from "../lib/mock-fetch";
import { Toaster } from "sonner";

const wrapper = ({ children }: { children: React.ReactNode }) => {
	return (
		<PortalAuthProvider>
			<Toaster />
			{children}
		</PortalAuthProvider>
	);
};

const mock = mockFetch();

const invoices = [
	{
		id: "inv_1",
		invoice_number: 1001,
		status: "sent",
		subtotal: 200,
		tax_amount: 16,
		total: 216,
		notes: "Screen repair",
		created_at: 1700000000000,
		due_date: 1705000000000,
		line_items: [],
		payments: [],
		total_paid: 0,
		balance_due: 216,
	},
	{
		id: "inv_2",
		invoice_number: 1002,
		status: "paid",
		subtotal: 100,
		tax_amount: 8,
		total: 108,
		notes: "Battery",
		created_at: 1700000000000,
		due_date: 1705000000000,
		line_items: [],
		payments: [],
		total_paid: 108,
		balance_due: 0,
	},
];

const invDetail = {
	invoice: {
		...invoices[0],
		line_items: [
			{ id: "li_1", description: "Screen replacement", quantity: 1, unit_price: 200, total: 200 },
		],
		payments: [],
		total_paid: 0,
		balance_due: 216,
	},
};

beforeEach(() => {
	mock.reset();
	localStorage.clear();
});

describe("PortalInvoicesPage", () => {
	it("renders invoice list", async () => {
		mock.push({ invoices });
		render(<PortalInvoicesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("My Invoices")).toBeTruthy();
		});
		await waitFor(() => {
			expect(screen.getByText("$216.00")).toBeTruthy();
		});
		expect(screen.getByText("$108.00")).toBeTruthy();
		expect(screen.getByText("#1001")).toBeTruthy();
	});

	it("shows invoice status badges", async () => {
		mock.push({ invoices });
		render(<PortalInvoicesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("sent")).toBeTruthy();
		});
		expect(screen.getByText("paid")).toBeTruthy();
	});

	it("expands invoice to show line items", async () => {
		mock.push({ invoices });
		mock.push(invDetail); // GET /api/portal/invoices/inv_1
		mock.push({ payment_methods: [] }); // saved cards
		render(<PortalInvoicesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("#1001")).toBeTruthy();
		});

		await userEvent.click(screen.getByText("#1001"));

		await waitFor(() => {
			expect(screen.getByText("Screen replacement")).toBeTruthy();
		});
	});

	it("initiates Stripe checkout when paying with a card", async () => {
		mock.push({ invoices });
		mock.push(invDetail);
		mock.push({ payment_methods: [] });
		mock.push({ session_id: "cs_1", url: "https://checkout.stripe.com/c/pay/cs_1" }); // checkout session
		render(<PortalInvoicesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("#1001")).toBeTruthy();
		});
		await userEvent.click(screen.getByText("#1001"));

		await waitFor(() => {
			expect(screen.getByText("Screen replacement")).toBeTruthy();
		});

		await userEvent.click(
			screen.getByText(/Pay \$.+ with Card/),
		);

		await waitFor(() => {
			expect(
				mock
					.calls()
					.some((c) => c.url.includes("create-checkout-session")),
			).toBe(true);
		});
	});

	it("shows error toast when invoices fail to load", async () => {
		mock.pushFail(500, "boom");
		render(<PortalInvoicesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Failed to load invoices")).toBeTruthy();
		});
	});

	it("shows empty state when no invoices", async () => {
		mock.push({ invoices: [] });
		render(<PortalInvoicesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/no invoices/i)).toBeTruthy();
		});
	});
});
