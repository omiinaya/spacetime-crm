/**
 * Regression tests for PaymentsPage.
 *
 * Coverage:
 *  - Currency display bug (ROADMAP 6D-1): "Total Collected" must be grouped
 *    per payment currency (p.currency), NOT labeled with the form's currency.
 *  - Empty state: "No payments yet" with a CTA.
 *  - Error state: a failed list fetch surfaces a visible error banner + retry.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import PaymentsPage from "@/pages/PaymentsPage";

const { mockPaymentsList, mockInvoicesList, mockCustomersList } = vi.hoisted(() => ({
  mockPaymentsList: vi.fn(),
  mockInvoicesList: vi.fn(),
  mockCustomersList: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  api: {
    payments: {
      list: (...args: any[]) => mockPaymentsList(...args),
      record: vi.fn(),
      delete: vi.fn(),
    },
    invoices: { list: (...args: any[]) => mockInvoicesList(...args) },
    customers: { list: (...args: any[]) => mockCustomersList(...args) },
  },
}));

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <PaymentsPage />
    </QueryClientProvider>
  );
}

/** Match the Total Collected amount line for a currency (formatCurrency + code suffix). */
function totalLine(currency: string, amount: string) {
  return screen.getByText((_content: string, el: Element | null) =>
    el?.tagName === "P" && el.textContent?.replace(/\s+/g, "") === `${amount}${currency}`
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockPaymentsList.mockResolvedValue({ payments: [], total: 0, offset: 0, limit: 25 });
  mockInvoicesList.mockResolvedValue({ invoices: [], total: 0 });
  mockCustomersList.mockResolvedValue({ customers: [], total: 0 });
});

describe("PaymentsPage currency display regression", () => {
  it("groups Total Collected per payment currency instead of using the form currency", async () => {
    mockPaymentsList.mockResolvedValue({
      payments: [
        { id: "p1", invoice_id: "i1", customer_id: "c1", amount: 100, method: "cash", reference: "", notes: "", created_at: 1700000000000, currency: "USD" },
        { id: "p2", invoice_id: "i2", customer_id: "c2", amount: 50, method: "credit", reference: "", notes: "", created_at: 1700000000000, currency: "EUR" },
        { id: "p3", invoice_id: "i3", customer_id: "c3", amount: 25, method: "cash", reference: "", notes: "", created_at: 1700000000000, currency: "USD" },
      ],
      total: 3,
      offset: 0,
      limit: 25,
    });

    renderPage();

    // USD payments (100 + 25) must total $125.00 under the USD group.
    await waitFor(() => {
      expect(totalLine("USD", "$125.00")).toBeInTheDocument();
    });
    // EUR payment (50) must show €50.00 under its own currency group.
    expect(totalLine("EUR", "€50.00")).toBeInTheDocument();
    // The bug was summing all currencies and labeling with form.currency:
    // "$175.00" must NOT appear (it never existed as a real total).
    expect(screen.queryByText("$175.00")).not.toBeInTheDocument();
  });

  it("shows a single USD total when all payments share the same currency", async () => {
    mockPaymentsList.mockResolvedValue({
      payments: [
        { id: "p1", invoice_id: "i1", customer_id: "c1", amount: 10, method: "cash", reference: "", notes: "", created_at: 1700000000000, currency: "USD" },
        { id: "p2", invoice_id: "i2", customer_id: "c2", amount: 5, method: "cash", reference: "", notes: "", created_at: 1700000000000, currency: "" },
      ],
      total: 2,
      offset: 0,
      limit: 25,
    });

    renderPage();

    // Empty currency defaults to USD — still one group under USD.
    await waitFor(() => {
      expect(totalLine("USD", "$15.00")).toBeInTheDocument();
    });
  });

  it("renders each payment row with its own currency", async () => {
    mockPaymentsList.mockResolvedValue({
      payments: [
        { id: "p1", invoice_id: "i1", customer_id: "c1", amount: 100, method: "cash", reference: "", notes: "", created_at: 1700000000000, currency: "USD" },
        { id: "p2", invoice_id: "i2", customer_id: "c2", amount: 50, method: "credit", reference: "", notes: "", created_at: 1700000000000, currency: "EUR" },
      ],
      total: 2,
      offset: 0,
      limit: 25,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getAllByText("$100.00").length).toBeGreaterThan(0);
      expect(screen.getAllByText("€50.00").length).toBeGreaterThan(0);
    });
  });
});

describe("PaymentsPage empty state", () => {
  it("shows 'No payments yet' with a Record Payment CTA when the list is empty", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("No payments yet")).toBeInTheDocument();
    });

    // Two "Record Payment" buttons: the header one + the empty-state CTA.
    const recordButtons = screen.getAllByRole("button", { name: /record payment/i });
    expect(recordButtons.length).toBe(2);

    // CTA opens the record form (Cancel button appears)
    const user = userEvent.setup();
    await user.click(recordButtons[1]);
    expect(await screen.findByRole("button", { name: /cancel/i })).toBeInTheDocument();
  });
});

describe("PaymentsPage error state", () => {
  it("shows an error banner instead of silently rendering an empty list", async () => {
    mockPaymentsList.mockRejectedValue(new Error("API 500: boom"));

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/failed to load payments/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
    // Empty state must NOT be shown when the fetch failed.
    expect(screen.queryByText("No payments yet")).not.toBeInTheDocument();
  });

  it("recovers when Retry succeeds", async () => {
    mockPaymentsList
      .mockRejectedValueOnce(new Error("API 500: boom"))
      .mockResolvedValueOnce({
        payments: [
          { id: "p1", invoice_id: "i1", customer_id: "c1", amount: 42, method: "cash", reference: "", notes: "", created_at: 1700000000000, currency: "USD" },
        ],
        total: 1,
        offset: 0,
        limit: 25,
      });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/failed to load payments/i)).toBeInTheDocument();
    });

    await userEvent.setup().click(screen.getByRole("button", { name: /retry/i }));

    await waitFor(() => {
      expect(totalLine("USD", "$42.00")).toBeInTheDocument();
    });
    expect(screen.queryByText(/failed to load payments/i)).not.toBeInTheDocument();
  });
});
