/**
 * Tests for PurchaseOrdersPage — list rendering, new PO form, PO detail view,
 * line item add, and status transitions.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PurchaseOrdersPage from "@/pages/PurchaseOrdersPage";
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

const poList = {
	purchase_orders: [
		{
			id: "po_1",
			vendor_name: "Acme Parts Co",
			po_number: 1001,
			status: "draft",
			approved_by: "",
			approved_at: 0,
			subtotal: 250,
			tax_amount: 20,
			shipping_cost: 10,
			total: 280,
			notes: "",
			created_at: 1700000000000,
			currency: "USD",
		},
		{
			id: "po_2",
			vendor_name: "Tech Supplies",
			po_number: 1002,
			status: "approved",
			approved_by: "u_1",
			approved_at: 1700000100000,
			subtotal: 100,
			tax_amount: 8,
			shipping_cost: 0,
			total: 108,
			notes: "",
			created_at: 1700000200000,
			currency: "USD",
		},
	],
	total: 2,
};

const poDetail = {
	purchase_order: {
		...poList.purchase_orders[0],
		line_items: [
			{
				id: "li_1",
				purchase_order_id: "po_1",
				product_id: "prod_1",
				description: "Laptop Battery",
				quantity: 2,
				unit_price: 100,
				total: 200,
				received_quantity: 0,
			},
			{
				id: "li_2",
				purchase_order_id: "po_1",
				product_id: "prod_2",
				description: "Charging Cable",
				quantity: 5,
				unit_price: 10,
				total: 50,
				received_quantity: 0,
			},
		],
	},
};

function pushList() {
	mock.push(poList); // /api/purchase-orders?offset=0&limit=25
}

beforeEach(() => {
	mock.reset();
});

describe("PurchaseOrdersPage", () => {
	it("renders page header and PO rows", async () => {
		pushList();
		render(<PurchaseOrdersPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Purchase Orders")).toBeTruthy();
		});
		expect(screen.getByText("Acme Parts Co")).toBeTruthy();
		expect(screen.getByText("Tech Supplies")).toBeTruthy();
	});

	it("shows New PO form on button click and creates", async () => {
		pushList();
		mock.push({ purchase_order: { id: "po_3" } }); // create response
		render(<PurchaseOrdersPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Purchase Orders")).toBeTruthy();
		});

		await userEvent.click(screen.getByText("New PO"));
		expect(screen.getByText("New Purchase Order")).toBeTruthy();

		await userEvent.type(
			screen.getByPlaceholderText("Vendor Name"),
			"New Vendor",
		);
		await userEvent.click(screen.getByText("Create"));
	});

	it("opens PO detail with line items on row click", async () => {
		pushList();
		mock.push(poDetail); // /api/purchase-orders/po_1
		render(<PurchaseOrdersPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Acme Parts Co")).toBeTruthy();
		});

		await userEvent.click(screen.getByText("Acme Parts Co"));

		await waitFor(() => {
			expect(screen.getByText("Laptop Battery")).toBeTruthy();
		});
		expect(screen.getByText("Charging Cable")).toBeTruthy();
	});

	it("adds a line item to the selected PO", async () => {
		pushList();
		mock.push(poDetail);
		mock.push({ ok: true }); // POST line item
		render(<PurchaseOrdersPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Acme Parts Co")).toBeTruthy();
		});
		await userEvent.click(screen.getByText("Acme Parts Co"));
		await waitFor(() => {
			expect(screen.getByText("Laptop Battery")).toBeTruthy();
		});

		await userEvent.click(screen.getByText("Add Item"));
		await waitFor(() => {
			expect(
				screen.getByPlaceholderText("Description (required)"),
			).toBeTruthy();
		});
		await userEvent.type(
			screen.getByPlaceholderText("Description (required)"),
			"Thermal Paste",
		);
		await userEvent.click(screen.getByText("Add"));
	});

	it("renders status badge text for draft and approved", async () => {
		pushList();
		render(<PurchaseOrdersPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Acme Parts Co")).toBeTruthy();
		});
		expect(screen.getByText("Draft")).toBeTruthy();
		expect(screen.getByText("Approved")).toBeTruthy();
	});

	it("shows empty state when no purchase orders", async () => {
		mock.push({ purchase_orders: [], total: 0 });
		render(<PurchaseOrdersPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Purchase Orders")).toBeTruthy();
		});
		await waitFor(() => {
			expect(screen.getByText(/no purchase orders/i)).toBeTruthy();
		});
	});

	it("renders PO detail totals", async () => {
		pushList();
		mock.push(poDetail);
		render(<PurchaseOrdersPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Acme Parts Co")).toBeTruthy();
		});
		await userEvent.click(screen.getByText("Acme Parts Co"));

		await waitFor(() => {
			expect(screen.getByText("Laptop Battery")).toBeTruthy();
		});
		// Total for the PO (280) appears in list card + detail card
		expect(screen.getAllByText("USD 280.00").length).toBeGreaterThan(0);
		expect(screen.getByText("USD 250.00")).toBeTruthy(); // subtotal
	});
});
