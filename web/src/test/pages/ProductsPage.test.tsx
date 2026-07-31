/**
 * Tests for ProductsPage — rendering, search, empty state, barcode lookup.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProductsPage from "@/pages/ProductsPage";
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

const product1 = {
	id: "prod_1",
	tenant_id: "t1",
	name: "Phone Screen",
	sku: "SCR-001",
	barcode: "123456789",
	description: "Replacement screen",
	category: "Parts",
	price: 29.99,
	cost: 12.5,
	quantity_on_hand: 50,
	quantity_committed: 5,
	quantity_available: 45,
	min_stock: 10,
	location: "Aisle-3",
	active: true,
	created_at: Date.now(),
	updated_at: Date.now(),
	reorder_quantity: 0,
};

const product2 = {
	id: "prod_2",
	tenant_id: "t1",
	name: "Battery",
	sku: "BAT-001",
	barcode: "987654321",
	description: "Replacement battery",
	category: "Parts",
	price: 19.99,
	cost: 8.0,
	quantity_on_hand: 5,
	quantity_committed: 0,
	quantity_available: 5,
	min_stock: 10,
	location: "Aisle-1",
	active: true,
	created_at: Date.now(),
	updated_at: Date.now(),
	reorder_quantity: 0,
};

function pushPage(products: unknown[], total = products.length) {
	mock.push({ categories: ["Parts", "Accessories"] }); // categories
	mock.push({ locations: ["Aisle-1", "Aisle-3"] }); // locations
	mock.push({ products, total, offset: 0, limit: 25 }); // products list
}

beforeEach(() => {
	mock.reset();
});

afterEach(() => {
	vi.clearAllTimers();
});

describe("ProductsPage", () => {
	it("renders page header and products from API", async () => {
		pushPage([product1, product2]);
		render(<ProductsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Products")).toBeTruthy();
			expect(screen.getByText("Phone Screen")).toBeTruthy();
			expect(screen.getByText("Battery")).toBeTruthy();
		});
	});

	it("shows empty state when no products exist", async () => {
		pushPage([]);
		render(<ProductsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/no products yet/i)).toBeTruthy();
		});
	});

	it("renders category filter options", async () => {
		pushPage([product1]);
		render(<ProductsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Phone Screen")).toBeTruthy();
		});
		// 'Parts' appears both as a category option and on the product badge
		expect(screen.getAllByText("Parts").length).toBeGreaterThanOrEqual(1);
		expect(screen.getAllByText("Accessories").length).toBeGreaterThanOrEqual(1);
	});

	it("searches products when typing", async () => {
		pushPage([product1, product2]);
		render(<ProductsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Phone Screen")).toBeTruthy();
		});

		const searchInput = screen.getByPlaceholderText(/search/i);
		await userEvent.type(searchInput, "Battery");
		await waitFor(() => {
			const calls = mock.calls();
			expect(calls.some((c) => c.url.includes("search=Battery"))).toBeTruthy();
		});
	});

	it("looks up a product by barcode", async () => {
		pushPage([product1]);
		mock.push({ product: product1 }); // barcode lookup

		render(<ProductsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Phone Screen")).toBeTruthy();
		});

		const barcodeInput = screen.getByPlaceholderText(/scan barcode/i);
		await userEvent.type(barcodeInput, "123456789");
		await userEvent.keyboard("{Enter}");

		await waitFor(() => {
			const calls = mock.calls();
			expect(
				calls.some((c) => c.url.includes("/products/by-barcode/123456789")),
			).toBeTruthy();
		});
	});
});
