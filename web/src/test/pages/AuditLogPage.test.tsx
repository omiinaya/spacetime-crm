/**
 * Tests for AuditLogPage — entry list rendering, entity/action filters,
 * and refresh.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AuditLogPage from "@/pages/AuditLogPage";
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

const entries = [
	{
		id: "aud_1",
		tenant_id: "t_1",
		user_id: "u_1",
		user_name: "Carlos",
		action: "create",
		entity: "customer",
		entity_id: "cust_1",
		details: '{"name":"Alice"}',
		created_at: 1700000000000,
	},
	{
		id: "aud_2",
		tenant_id: "t_1",
		user_id: "u_2",
		user_name: "Bob",
		action: "delete",
		entity: "invoice",
		entity_id: "inv_9",
		details: "",
		created_at: 1700000100000,
	},
];

beforeEach(() => {
	mock.reset();
});

describe("AuditLogPage", () => {
	it("renders page header and audit entries", async () => {
		mock.push({ entries });
		render(<AuditLogPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Audit Log")).toBeTruthy();
		});
		await waitFor(() => {
			expect(screen.getByText("Carlos")).toBeTruthy();
		});
		expect(screen.getByText("Bob")).toBeTruthy();
	});

	it("shows action badges (create/delete)", async () => {
		mock.push({ entries });
		render(<AuditLogPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("create")).toBeTruthy();
		});
		expect(screen.getByText("delete")).toBeTruthy();
	});

	it("filters by entity via select", async () => {
		mock.push({ entries });
		mock.push({ entries: [entries[0]] }); // filtered response
		render(<AuditLogPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Audit Log")).toBeTruthy();
		});

		await userEvent.selectOptions(
			screen.getAllByRole("combobox")[0],
			"customer",
		);

		await waitFor(() => {
			const urls = mock.calls().map((c) => c.url);
			expect(urls.some((u) => u.includes("entity=customer"))).toBe(true);
		});
	});

	it("refreshes when refresh button clicked", async () => {
		mock.push({ entries });
		render(<AuditLogPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Audit Log")).toBeTruthy();
		});
		const before = mock.calls().length;
		await userEvent.click(screen.getByText("Refresh"));
		await waitFor(() => {
			expect(mock.calls().length).toBeGreaterThan(before);
		});
	});

	it("shows error toast on failure", async () => {
		mock.pushFail(500);
		render(<AuditLogPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/failed to load audit log/i)).toBeTruthy();
		});
	});

	it("shows empty state when no entries", async () => {
		mock.push({ entries: [] });
		render(<AuditLogPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/no audit/i)).toBeTruthy();
		});
	});
});
