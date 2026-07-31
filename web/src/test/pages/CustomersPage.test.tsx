/**
 * Tests for CustomersPage — rendering, search, create form, edit, delete.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CustomersPage from "@/pages/CustomersPage";
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
	balance: 25.5,
	created_at: Date.now(),
};

const customerBob = {
	id: "cust_2",
	first_name: "Bob",
	last_name: "Smith",
	email: "bob@example.com",
	phone: "",
	mobile: "+15553334444",
	company: "",
	balance: 0,
	created_at: Date.now(),
};

function pushCustomerList(customers: unknown[], total = customers.length) {
	mock.push({ customers, total, offset: 0, limit: 25 });
	mock.push({ duplicates: [], count: 0 });
}

/** Push the three activity fetches fired when a detail panel expands:
 * tickets → invoices → appointments (React Query hook order). */
function pushActivity(
	tickets: unknown[] = [],
	invoices: unknown[] = [],
	appointments: unknown[] = [],
) {
	mock.push({ tickets, total: tickets.length, offset: 0, limit: 5 });
	mock.push({ invoices, total: invoices.length, offset: 0, limit: 5 });
	mock.push({ appointments, total: appointments.length, offset: 0, limit: 5 });
}

beforeEach(() => {
	mock.reset();
});

afterEach(() => {
	vi.clearAllTimers();
});

describe("CustomersPage", () => {
	it("renders page header while loading", () => {
		render(<CustomersPage />, { wrapper });
		expect(screen.getByText(/manage your customer database/i)).toBeTruthy();
	});

	it("shows empty state when no customers exist", async () => {
		pushCustomerList([]);
		render(<CustomersPage />, { wrapper });
		await waitFor(() => {
			expect(screen.getByText(/manage your customer database/i)).toBeTruthy();
			expect(screen.getByText(/no customers yet/i)).toBeTruthy();
		});
	});

	it("renders customers from the API", async () => {
		pushCustomerList([customerAlice, customerBob]);
		render(<CustomersPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Alice Johnson")).toBeTruthy();
			expect(screen.getByText("Bob Smith")).toBeTruthy();
			expect(screen.getByText("alice@example.com")).toBeTruthy();
		});
	});

	it("searches customers when typing in search box", async () => {
		pushCustomerList([customerAlice, customerBob]);
		render(<CustomersPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Alice Johnson")).toBeTruthy();
		});

		const searchInput = screen.getByPlaceholderText(/search/i);
		await userEvent.type(searchInput, "Bob");
		await waitFor(() => {
			const calls = mock.calls();
			expect(calls.some((c) => c.url.includes("search=Bob"))).toBeTruthy();
		});
	});

	it("opens create form and saves a new customer", async () => {
		pushCustomerList([]);
		// 3rd call: POST /customers (create)
		mock.push({ ok: true });

		render(<CustomersPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/no customers yet/i)).toBeTruthy();
		});

		const addBtn = screen.getByRole("button", { name: /add customer/i });
		await userEvent.click(addBtn);

		const firstName = screen.getByPlaceholderText(/first name/i);
		const lastName = screen.getByPlaceholderText(/last name/i);
		const email = screen.getByPlaceholderText(/email/i);
		await userEvent.type(firstName, "New");
		await userEvent.type(lastName, "Person");
		await userEvent.type(email, "new@example.com");

		const saveBtn = screen.getByRole("button", { name: /^create$/i });
		await userEvent.click(saveBtn);

		await waitFor(() => {
			const calls = mock.calls();
			const post = calls.find(
				(c) => c.init?.method === "POST" && c.url.includes("/customers"),
			);
			expect(post).toBeTruthy();
			const body = JSON.parse(String(post!.init!.body));
			expect(body.first_name).toBe("New");
			expect(body.last_name).toBe("Person");
		});
	});

	it("shows duplicate badge when duplicates exist", async () => {
		mock.push({ customers: [], total: 0, offset: 0, limit: 25 });
		mock.push({
			duplicates: [
				{
					field: "email",
					value: "alice@example.com",
					customers: [customerAlice, customerAlice],
				},
			],
			count: 2,
		});
		render(<CustomersPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/2 duplicates found/i)).toBeTruthy();
		});
	});

	it("deletes a customer", async () => {
		pushCustomerList([customerAlice]);
		mock.push({ ok: true }); // DELETE

		render(<CustomersPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Alice Johnson")).toBeTruthy();
		});

		const deleteBtn = screen.getAllByRole("button", { name: /delete/i })[0];
		await userEvent.click(deleteBtn);

		await waitFor(() => {
			const calls = mock.calls();
			expect(
				calls.some(
					(c) =>
						c.init?.method === "DELETE" && c.url.includes("/customers/cust_1"),
				),
			).toBeTruthy();
		});
	});

	it("shows unified activity timeline with tickets, invoices, appointments sorted newest first", async () => {
		pushCustomerList([customerAlice]);
		// Fixed timestamps so ordering is deterministic (appointment newest).
		const day = 86_400_000;
		pushActivity(
			[
				{
					id: "t_1",
					ticket_number: 101,
					title: "Screen repair",
					status: "in_progress",
					created_at: 1_752_000_000_000 + 3 * day,
				},
			],
			[
				{
					id: "i_1",
					invoice_number: 5001,
					status: "sent",
					total: 199.99,
					currency: "USD",
					created_at: 1_752_000_000_000 + 1 * day,
				},
			],
			[
				{
					id: "a_1",
					title: "Follow-up call",
					status: "scheduled",
					start_time: 1_752_000_000_000 + 5 * day,
				},
			],
		);

		render(<CustomersPage />, { wrapper });

		// Expand the panel
		await waitFor(() => {
			expect(screen.getByText("Alice Johnson")).toBeTruthy();
		});
		await userEvent.click(screen.getByText("Alice Johnson"));

		await waitFor(() => {
			expect(screen.getByText(/activity timeline/i)).toBeTruthy();
		});

		// Appointments are fetched with the customer_id filter
		await waitFor(() => {
			const calls = mock.calls();
			expect(
				calls.some((c) => c.url.includes("/appointments?customer_id=cust_1")),
			).toBeTruthy();
			expect(
				calls.some((c) => c.url.includes("/tickets?customer_id=cust_1")),
			).toBeTruthy();
			expect(
				calls.some((c) => c.url.includes("/invoices?customer_id=cust_1")),
			).toBeTruthy();
		});

		// All three entity types render
		expect(screen.getByText(/screen repair/i)).toBeTruthy();
		expect(screen.getByText(/invoice #5001/i)).toBeTruthy();
		expect(screen.getByText(/follow-up call/i)).toBeTruthy();

		// Timeline order: appointment (5d) → ticket (3d) → invoice (1d)
		const timelineButtons = screen
			.getAllByRole("button")
			.filter((b) => b.getAttribute("title")?.startsWith("Open "));
		expect(timelineButtons).toHaveLength(3);
		const labels = timelineButtons.map((b) => b.textContent ?? "");
		const apptIdx = labels.findIndex((l) => l.includes("Follow-up call"));
		const ticketIdx = labels.findIndex((l) => l.includes("Screen repair"));
		const invoiceIdx = labels.findIndex((l) => l.includes("Invoice #5001"));
		expect(apptIdx).toBeGreaterThan(-1);
		expect(ticketIdx).toBeGreaterThan(apptIdx);
		expect(invoiceIdx).toBeGreaterThan(ticketIdx);
	});

	it("shows empty state when customer has no activity", async () => {
		pushCustomerList([customerAlice]);
		pushActivity(); // all three empty

		render(<CustomersPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Alice Johnson")).toBeTruthy();
		});
		await userEvent.click(screen.getByText("Alice Johnson"));

		await waitFor(() => {
			expect(screen.getByText(/no activity yet/i)).toBeTruthy();
		});
	});

	it("navigates to entity pages when timeline events are clicked", async () => {
		pushCustomerList([customerAlice]);
		pushActivity(
			[{ id: "t_1", ticket_number: 101, title: "Screen repair", status: "open", created_at: 1_752_000_000_000 }],
			[{ id: "i_1", invoice_number: 5001, status: "paid", total: 99.0, currency: "USD", created_at: 1_751_000_000_000 }],
			[{ id: "a_1", title: "Follow-up call", status: "completed", start_time: 1_753_000_000_000 }],
		);

		const navigate = vi.fn();
		render(<CustomersPage onNavigate={navigate} />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Alice Johnson")).toBeTruthy();
		});
		await userEvent.click(screen.getByText("Alice Johnson"));

		await waitFor(() => {
			expect(screen.getByText(/activity timeline/i)).toBeTruthy();
		});

		await userEvent.click(screen.getByTitle(/open ticket — #101 screen repair/i));
		expect(navigate).toHaveBeenCalledWith("tickets");

		await userEvent.click(screen.getByTitle(/open invoice — invoice #5001/i));
		expect(navigate).toHaveBeenCalledWith("invoices");

		await userEvent.click(screen.getByTitle(/open appointment — follow-up call/i));
		expect(navigate).toHaveBeenCalledWith("appointments");
	});
});
