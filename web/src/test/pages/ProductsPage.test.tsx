/**
 * Tests for ProductsPage empty + error states (ROADMAP 6B-2 / 6A).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProductsPage from "@/pages/ProductsPage";

const { mockProductsList, mockCategories, mockLowStock } = vi.hoisted(() => ({
  mockProductsList: vi.fn(),
  mockCategories: vi.fn(),
  mockLowStock: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: {
    products: {
      list: (...args: any[]) => mockProductsList(...args),
      categories: (...args: any[]) => mockCategories(...args),
      lowStock: { list: (...args: any[]) => mockLowStock(...args) },
      adjustments: { list: vi.fn(), create: vi.fn() },
      create: vi.fn(),
      transfer: vi.fn(),
      byBarcode: vi.fn(),
    },
  },
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ user: { id: "u1" } }),
}));

vi.mock("../components/BarcodeLabel", () => ({
  printBarcodeLabel: vi.fn(),
}));

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <ProductsPage />
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockProductsList.mockResolvedValue({ products: [], total: 0, offset: 0, limit: 25 });
  mockCategories.mockResolvedValue({ categories: [] });
  mockLowStock.mockResolvedValue({ products: [], count: 0 });
});

describe("ProductsPage empty state", () => {
  it("shows 'No products yet' with an Add Product CTA when the list is empty", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("No products yet")).toBeInTheDocument();
    });

    const addButtons = screen.getAllByRole("button", { name: /add product/i });
    expect(addButtons.length).toBeGreaterThanOrEqual(2); // header + empty-state CTA

    // CTA opens the create form
    const user = userEvent.setup();
    await user.click(addButtons[addButtons.length - 1]);
    expect(await screen.findByText("New Product")).toBeInTheDocument();
  });
});

describe("ProductsPage error state", () => {
  it("shows an error banner instead of the empty state when the list fetch fails", async () => {
    mockProductsList.mockRejectedValue(new Error("API 500: boom"));

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/failed to load products/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
    expect(screen.queryByText("No products yet")).not.toBeInTheDocument();
  });

  it("recovers when Retry succeeds", async () => {
    mockProductsList
      .mockRejectedValueOnce(new Error("API 500: boom"))
      .mockResolvedValueOnce({
        products: [
          { id: "pr1", name: "Logic Board", sku: "LB-1", barcode: "", description: "", category: "", price: 299, cost: 150, quantity_on_hand: 5, quantity_committed: 0, quantity_available: 5, min_stock: 0, location: "", active: true, created_at: 1700000000000 },
        ],
        total: 1,
        offset: 0,
        limit: 25,
      });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/failed to load products/i)).toBeInTheDocument();
    });

    await userEvent.setup().click(screen.getByRole("button", { name: /retry/i }));

    await waitFor(() => {
      expect(screen.getByText("Logic Board")).toBeInTheDocument();
    });
    expect(screen.queryByText(/failed to load products/i)).not.toBeInTheDocument();
  });
});
