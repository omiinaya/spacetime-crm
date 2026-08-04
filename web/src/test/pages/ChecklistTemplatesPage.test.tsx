/**
 * Tests for ChecklistTemplatesPage — template list, create template with
 * items, and delete.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ChecklistTemplatesPage from "@/pages/ChecklistTemplatesPage";
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

const templates = [
	{
		id: "clt_1",
		name: "Standard PC Repair",
		description: "Default repair checklist",
		items: JSON.stringify([
			{ label: "Diagnose", sort_order: 0 },
			{ label: "Test hardware", sort_order: 1 },
		]),
		created_at: 1700000000000,
		updated_at: 1700000000000,
	},
	{
		id: "clt_2",
		name: "Phone Screen Install",
		description: "",
		items: "[]",
		created_at: 1700000000000,
		updated_at: 1700000000000,
	},
];

beforeEach(() => {
	mock.reset();
});

describe("ChecklistTemplatesPage", () => {
	it("renders template list", async () => {
		mock.push({ templates });
		render(<ChecklistTemplatesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Standard PC Repair")).toBeTruthy();
		});
		expect(screen.getByText("Phone Screen Install")).toBeTruthy();
	});

	it("shows item count for templates", async () => {
		mock.push({ templates });
		render(<ChecklistTemplatesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Standard PC Repair")).toBeTruthy();
		});
		// 2 items parsed from JSON
		expect(screen.getByText(/2 items/)).toBeTruthy();
	});

	it("opens create form and creates a template", async () => {
		mock.push({ templates });
		mock.push({ ok: true }); // POST /api/checklist-templates
		render(<ChecklistTemplatesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Standard PC Repair")).toBeTruthy();
		});

		await userEvent.click(screen.getByText(/new template/i));
		await waitFor(() => {
			expect(
				screen.getByPlaceholderText("e.g. Standard PC Repair"),
			).toBeTruthy();
		});

		await userEvent.type(
			screen.getByPlaceholderText("e.g. Standard PC Repair"),
			"Data Backup",
		);
		await userEvent.click(screen.getByText("Create Template"));

		await waitFor(() => {
			expect(mock.calls().some((c) => c.init?.method === "POST")).toBe(true);
		});
	});

	it("shows empty state when no templates", async () => {
		mock.push({ templates: [] });
		render(<ChecklistTemplatesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("No checklist templates yet")).toBeTruthy();
		});
	});

	it("deletes a template via trash button", async () => {
		vi.spyOn(window, "confirm").mockReturnValue(true);
		mock.push({ templates });
		mock.push({ ok: true }); // DELETE /api/checklist-templates/clt_1
		render(<ChecklistTemplatesPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Standard PC Repair")).toBeTruthy();
		});

		const buttons = screen.getAllByRole("button");
		// Last button is the last row's trash button.
		await userEvent.click(buttons[buttons.length - 1]);

		await waitFor(() => {
			expect(mock.calls().some((c) => c.init?.method === "DELETE")).toBe(true);
		});
	});
});
