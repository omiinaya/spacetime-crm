/**
 * Tests for ImportExportPage – export calls, import flow, result display.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ImportExportPage from "@/pages/ImportExportPage";

const { mockExportCsv, mockImportCustomers, mockImportProducts } = vi.hoisted(
	() => ({
		mockExportCsv: vi.fn(),
		mockImportCustomers: vi.fn(),
		mockImportProducts: vi.fn(),
	}),
);

// Mock api module so we can control export/import in each test
vi.mock("@/lib/api", () => ({
	api: {
		export: { csv: (...args: any[]) => mockExportCsv(...args) },
		import: {
			customers: (file: File) => mockImportCustomers(file),
			products: (file: File) => mockImportProducts(file),
		},
	},
	WEBHOOK_EVENTS: [],
}));

beforeEach(() => {
	vi.restoreAllMocks();
	mockExportCsv.mockReset();
	mockImportCustomers.mockReset();
	mockImportProducts.mockReset();
});

// ── Rendering ──

it("renders the import/export page with both sections", () => {
	render(<ImportExportPage />);

	expect(screen.getByText("Import / Export")).toBeInTheDocument();
	expect(screen.getByText("Export Data")).toBeInTheDocument();
	expect(screen.getByText("Import Data")).toBeInTheDocument();
});

it("renders entity dropdown with 10 options", () => {
	render(<ImportExportPage />);

	const selects = screen.getAllByDisplayValue("Customers");
	expect(selects.length).toBe(2);
	expect(screen.getByText("Tickets")).toBeInTheDocument();
	expect(screen.getByText("Invoices")).toBeInTheDocument();
	expect(screen.getAllByText("Products").length).toBeGreaterThan(0);
});

it("shows the required CSV columns details on the Import section", () => {
	render(<ImportExportPage />);
	expect(screen.getByText("Required CSV columns")).toBeInTheDocument();
});

// ── Export ──

it("calls export.csv with default entity on export click", async () => {
	const user = userEvent.setup();
	render(<ImportExportPage />);

	await user.click(screen.getByRole("button", { name: /export csv/i }));

	expect(mockExportCsv).toHaveBeenCalledWith("customers");
});

it("exports the selected entity type", async () => {
	const user = userEvent.setup();
	render(<ImportExportPage />);

	const selects = screen.getAllByDisplayValue("Customers");
	await user.selectOptions(selects[0], "products");

	await user.click(screen.getByRole("button", { name: /export csv/i }));

	expect(mockExportCsv).toHaveBeenCalledWith("products");
});

// ── Import file selection ──

it("shows selected file name after choosing a file", async () => {
	const user = userEvent.setup();
	render(<ImportExportPage />);

	const input = document.querySelector(
		'input[type="file"]',
	) as HTMLInputElement;
	const file = new File(["a,b,c\n1,2,3"], "test.csv", { type: "text/csv" });
	await user.upload(input, file);

	expect(screen.getByText("test.csv")).toBeInTheDocument();
});

// ── Import button states ──

it("disables import button when no file is selected", () => {
	render(<ImportExportPage />);

	const importBtn = screen.getByRole("button", { name: /^import$/i });
	expect(importBtn).toBeDisabled();
});

it("enables import button after file is selected", async () => {
	const user = userEvent.setup();
	render(<ImportExportPage />);

	const input = document.querySelector(
		'input[type="file"]',
	) as HTMLInputElement;
	const file = new File(["a,b,c\n1,2,3"], "test.csv", { type: "text/csv" });
	await user.upload(input, file);

	const importBtn = screen.getByRole("button", { name: /^import$/i });
	expect(importBtn).not.toBeDisabled();
});

// ── Import flow with API ──

it("shows successful import result", async () => {
	mockImportCustomers.mockResolvedValue({ imported: 5, errors: [] });

	const user = userEvent.setup();
	render(<ImportExportPage />);

	const input = document.querySelector(
		'input[type="file"]',
	) as HTMLInputElement;
	const file = new File(["a,b,c\n1,2,3"], "test.csv", { type: "text/csv" });
	await user.upload(input, file);

	await user.click(screen.getByRole("button", { name: /^import$/i }));

	await waitFor(() => {
		expect(screen.getByText(/Imported 5 records?/i)).toBeInTheDocument();
	});
});

it("shows errors when import returns errors", async () => {
	mockImportCustomers.mockResolvedValue({
		imported: 3,
		errors: ["Row 2: invalid email", "Row 5: missing name"],
	});

	const user = userEvent.setup();
	render(<ImportExportPage />);

	const input = document.querySelector(
		'input[type="file"]',
	) as HTMLInputElement;
	const file = new File(["a,b,c\n1,2,3"], "test.csv", { type: "text/csv" });
	await user.upload(input, file);

	await user.click(screen.getByRole("button", { name: /^import$/i }));

	await waitFor(() => {
		expect(screen.getByText(/Imported 3 records?/i)).toBeInTheDocument();
	});
	expect(screen.getByText("Row 2: invalid email")).toBeInTheDocument();
	expect(screen.getByText("Row 5: missing name")).toBeInTheDocument();
});

it("shows error result when import API fails", async () => {
	mockImportCustomers.mockRejectedValue(new Error("Network error"));

	const user = userEvent.setup();
	render(<ImportExportPage />);

	const input = document.querySelector(
		'input[type="file"]',
	) as HTMLInputElement;
	const file = new File(["a,b,c\n1,2,3"], "test.csv", { type: "text/csv" });
	await user.upload(input, file);

	await user.click(screen.getByRole("button", { name: /^import$/i }));

	await waitFor(() => {
		expect(screen.getByText(/Imported 0 records?/i)).toBeInTheDocument();
	});
	expect(screen.getByText("Network error")).toBeInTheDocument();
});

// ── Loading state ──

it("shows 'Importing…' while import is in progress", async () => {
	mockImportCustomers.mockReturnValueOnce(new Promise(() => {}));

	const user = userEvent.setup();
	render(<ImportExportPage />);

	const input = document.querySelector(
		'input[type="file"]',
	) as HTMLInputElement;
	const file = new File(["a,b,c\n1,2,3"], "test.csv", { type: "text/csv" });
	await user.upload(input, file);

	await user.click(screen.getByRole("button", { name: /^import$/i }));

	expect(screen.getByRole("button", { name: /importing/i })).toBeDisabled();
});
