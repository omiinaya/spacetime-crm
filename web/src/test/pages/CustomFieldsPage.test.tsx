/**
 * Tests for CustomFieldsPage — definition list, entity filter, create form,
 * and delete.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CustomFieldsPage from "@/pages/CustomFieldsPage";
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

const definitions = [
	{
		id: "cfd_1",
		entity_type: "customer",
		label: "Preferred Language",
		field_type: "text",
		options: "",
		sort_order: 1,
		required: false,
		active: true,
		created_at: 1700000000000,
		updated_at: 1700000000000,
	},
	{
		id: "cfd_2",
		entity_type: "ticket",
		label: "Warranty Until",
		field_type: "date",
		options: "",
		sort_order: 2,
		required: true,
		active: true,
		created_at: 1700000000000,
		updated_at: 1700000000000,
	},
];

beforeEach(() => {
	mock.reset();
});

describe("CustomFieldsPage", () => {
	it("renders field definitions", async () => {
		mock.push({ definitions });
		render(<CustomFieldsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Preferred Language")).toBeTruthy();
		});
		expect(screen.getByText("Warranty Until")).toBeTruthy();
	});

	it("shows entity badges and field types", async () => {
		mock.push({ definitions });
		render(<CustomFieldsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Preferred Language")).toBeTruthy();
		});
		expect(screen.getByText("customer")).toBeTruthy();
		expect(screen.getByText("ticket")).toBeTruthy();
		expect(screen.getByText("text")).toBeTruthy();
		expect(screen.getByText("date")).toBeTruthy();
	});

	it("filters by entity via chip button", async () => {
		mock.push({ definitions });
		mock.push({ definitions: [definitions[0]] });
		render(<CustomFieldsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Preferred Language")).toBeTruthy();
		});

		await userEvent.click(screen.getByText("Customers"));

		await waitFor(() => {
			expect(
				mock.calls().some((c) => c.url.includes("entity_type=customer")),
			).toBe(true);
		});
	});

	it("opens create form and creates a field", async () => {
		mock.push({ definitions });
		mock.push({ ok: true }); // POST /api/custom-field-definitions
		render(<CustomFieldsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Preferred Language")).toBeTruthy();
		});

		await userEvent.click(screen.getByText("Add Field"));
		await waitFor(() => {
			expect(screen.getByText("New Custom Field")).toBeTruthy();
		});

		await userEvent.type(
			screen.getByPlaceholderText("e.g. Serial Number"),
			"Serial Number",
		);
		await userEvent.click(screen.getByText("Save"));

		await waitFor(() => {
			expect(mock.calls().some((c) => c.init?.method === "POST")).toBe(true);
		});
	});

	it("shows empty state when no fields", async () => {
		mock.push({ definitions: [] });
		render(<CustomFieldsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/no custom fields/i)).toBeTruthy();
		});
	});

	it("deletes a field via trash button", async () => {
		vi.spyOn(window, "confirm").mockReturnValue(true);
		mock.push({ definitions });
		mock.push({ ok: true }); // DELETE /api/custom-field-definitions/cfd_1
		render(<CustomFieldsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Preferred Language")).toBeTruthy();
		});

		// Trash buttons are the trailing ghost icon buttons in each row;
		// the final button on the page is the last row's trash button.
		const buttons = screen.getAllByRole("button");
		await userEvent.click(buttons[buttons.length - 1]);

		await waitFor(() => {
			expect(mock.calls().some((c) => c.init?.method === "DELETE")).toBe(true);
		});
	});
});
