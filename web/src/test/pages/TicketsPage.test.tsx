/**
 * Tests for TicketsPage — rendering, filters, create form, SLA breach badge.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TicketsPage from "@/pages/TicketsPage";
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

const customerAlice = {
	id: "cust_1",
	first_name: "Alice",
	last_name: "Johnson",
	email: "alice@example.com",
	phone: "+15551112222",
	mobile: "",
	company: "Acme",
	balance: 0,
	created_at: Date.now(),
};

const ticket1 = {
	id: "tkt_1",
	ticket_number: 1001,
	tenant_id: "t1",
	customer_id: "cust_1",
	title: "Broken screen",
	description: "Cracked glass",
	status: "new",
	priority: "high",
	assigned_user_id: "",
	created_at: Date.now() - 3600000, // 1h ago
	updated_at: Date.now() - 3600000,
};

const ticket2 = {
	id: "tkt_2",
	ticket_number: 1002,
	tenant_id: "t1",
	customer_id: "cust_1",
	title: "Battery replacement",
	description: "",
	status: "in_progress",
	priority: "medium",
	assigned_user_id: "user_1",
	created_at: Date.now() - 7200000, // 2h ago
	updated_at: Date.now() - 7200000,
};

function pushPage(
	customers: unknown[],
	tickets: unknown[],
	total = tickets.length,
) {
	mock.push({ tickets, total, offset: 0, limit: 25 }); // tickets list
	mock.push({ customers, total: customers.length, offset: 0, limit: 25 }); // customers list
	mock.push({ count: 0, breaches: [] }); // sla breaches
}

beforeEach(() => {
	mock.reset();
});

afterEach(() => {
	vi.clearAllTimers();
});

describe("TicketsPage", () => {
	it("renders page header and filter buttons", async () => {
		pushPage([customerAlice], []);
		render(<TicketsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Tickets")).toBeTruthy();
			expect(screen.getByText(/manage repair tickets/i)).toBeTruthy();
			expect(screen.getByRole("button", { name: /new ticket/i })).toBeTruthy();
		});
		// Filter buttons exist
		expect(screen.getByRole("button", { name: /^All$/i })).toBeTruthy();
		expect(screen.getByRole("button", { name: /in_progress/i })).toBeTruthy();
	});

	it("renders tickets from the API", async () => {
		pushPage([customerAlice], [ticket1, ticket2]);
		render(<TicketsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Broken screen")).toBeTruthy();
			expect(screen.getByText("Battery replacement")).toBeTruthy();
			expect(screen.getByText("#1001")).toBeTruthy();
			expect(screen.getByText("#1002")).toBeTruthy();
		});
	});

	it("shows SLA breach badge when breaches exist", async () => {
		mock.push({ tickets: [], total: 0, offset: 0, limit: 25 });
		mock.push({ customers: [customerAlice], total: 1, offset: 0, limit: 25 });
		mock.push({
			count: 2,
			breaches: [{ id: "tkt_1" }, { id: "tkt_2" }],
		});
		render(<TicketsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/2 SLA breaches/i)).toBeTruthy();
		});
	});

	it("opens the new ticket form", async () => {
		pushPage([customerAlice], []);
		render(<TicketsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByRole("button", { name: /new ticket/i })).toBeTruthy();
		});

		const newBtn = screen.getByRole("button", { name: /new ticket/i });
		await userEvent.click(newBtn);

		await waitFor(() => {
			expect(screen.getByText(/select customer/i)).toBeTruthy();
			expect(screen.getByPlaceholderText("Title")).toBeTruthy();
			expect(screen.getByPlaceholderText("Description")).toBeTruthy();
		});
	});

	it("creates a new ticket with form data", async () => {
		pushPage([customerAlice], []);
		mock.push({ ok: true }); // POST /tickets

		render(<TicketsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByRole("button", { name: /new ticket/i })).toBeTruthy();
		});

		const newBtn = screen.getByRole("button", { name: /new ticket/i });
		await userEvent.click(newBtn);

		const titleInput = screen.getByPlaceholderText("Title");
		await userEvent.type(titleInput, "Laptop won't boot");

		const createBtn = screen.getByRole("button", { name: /^create$/i });
		await userEvent.click(createBtn);

		await waitFor(() => {
			const calls = mock.calls();
			const post = calls.find(
				(c) => c.init?.method === "POST" && c.url.includes("/tickets"),
			);
			expect(post).toBeTruthy();
			const body = JSON.parse(String(post!.init!.body));
			expect(body.title).toBe("Laptop won't boot");
		});
	});

	it("filters tickets by status", async () => {
		pushPage([customerAlice], [ticket1, ticket2]);
		render(<TicketsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Broken screen")).toBeTruthy();
		});

		const inProgressBtn = screen.getByRole("button", { name: /in_progress/i });
		await userEvent.click(inProgressBtn);

		await waitFor(() => {
			const calls = mock.calls();
			expect(
				calls.some(
					(c) =>
						c.url.includes("/tickets") && c.url.includes("status=in_progress"),
				),
			).toBeTruthy();
		});
	});
});
