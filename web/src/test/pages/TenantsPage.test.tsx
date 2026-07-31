/**
 * Tests for TenantsPage — tenant list, member loading, create form,
 * and error handling.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TenantsPage from "@/pages/TenantsPage";
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

const tenantsData = {
	tenants: [
		{
			id: "t_1",
			name: "Acme Repair",
			slug: "acme",
			logo_url: "",
			settings: "{}",
			created_at: 1700000000000,
			updated_at: 1700000000000,
		},
		{
			id: "t_2",
			name: "Bob's Shop",
			slug: "bobs",
			logo_url: "",
			settings: "{}",
			created_at: 1700000000000,
			updated_at: 1700000000000,
		},
	],
};

const tenantDetail = {
	tenant: {
		...tenantsData.tenants[0],
		members: [
			{ id: "m_1", tenant_id: "t_1", username: "alice", role: "admin" },
			{ id: "m_2", tenant_id: "t_1", username: "bob", role: "tech" },
		],
	},
};

beforeEach(() => {
	mock.reset();
	localStorage.clear();
});

describe("TenantsPage", () => {
	it("renders tenant list", async () => {
		mock.push(tenantsData);
		render(<TenantsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Acme Repair")).toBeTruthy();
		});
		expect(screen.getByText("Bob's Shop")).toBeTruthy();
	});

	it("loads and shows members when a tenant is selected", async () => {
		mock.push(tenantsData);
		mock.push(tenantDetail);
		render(<TenantsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Acme Repair")).toBeTruthy();
		});

		await userEvent.click(screen.getByText("Acme Repair"));

		await waitFor(() => {
			expect(screen.getByText("alice")).toBeTruthy();
		});
		expect(screen.getByText("bob")).toBeTruthy();
	});

	it("opens create form and creates a tenant", async () => {
		// Seed an admin session so the "New Tenant" button (isAdmin-gated) shows.
		const payload = btoa(
			JSON.stringify({
				sub: "u_admin",
				name: "Admin",
				email: "admin@test.com",
				role: "admin",
				tenant_id: "t_1",
			}),
		);
		localStorage.setItem("crm_token", `x.${payload}.sig`);

		mock.push(tenantsData);
		mock.push({ ok: true }); // POST /api/tenants
		mock.push(tenantsData); // reload after create
		render(<TenantsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Acme Repair")).toBeTruthy();
		});

		await userEvent.click(screen.getByText("New Tenant"));
		await waitFor(() => {
			expect(screen.getByPlaceholderText("My Repair Shop")).toBeTruthy();
		});

		await userEvent.type(
			screen.getByPlaceholderText("My Repair Shop"),
			"New Shop",
		);
		await userEvent.click(screen.getByText("Create"));

		await waitFor(() => {
			expect(mock.calls().some((c) => c.init?.method === "POST")).toBe(true);
		});
		localStorage.removeItem("crm_token");
	});

	it("shows error toast when tenant list fails", async () => {
		mock.pushFail(500, "Server exploded");
		render(<TenantsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/Server exploded/i)).toBeTruthy();
		});
	});

	it("shows empty state when no tenants", async () => {
		mock.push({ tenants: [] });
		render(<TenantsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/no tenants/i)).toBeTruthy();
		});
	});
});
