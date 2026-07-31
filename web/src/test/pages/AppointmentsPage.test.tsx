/**
 * Tests for AppointmentsPage — rendering, calendar day selection, new form.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AppointmentsPage from "@/pages/AppointmentsPage";
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

const today = new Date();
today.setHours(10, 0, 0, 0);
const apptTodayStart = today.getTime();

const appt1 = {
	id: "appt_1",
	tenant_id: "t1",
	customer_id: "cust_1",
	title: "Screen replacement",
	description: "",
	start_time: apptTodayStart, // today at 10am — matches the default selected day
	end_time: apptTodayStart + 3600000,
	status: "scheduled",
	tech_id: "",
	created_at: Date.now(),
};

function pushPage(appts: unknown[], total = appts.length) {
	mock.push({ appointments: appts, total, offset: 0, limit: 50 }); // appointments
	mock.push({ customers: [customerAlice], total: 1, offset: 0, limit: 25 }); // customers
	mock.push({ recurring: [] }); // recurring series
}

beforeEach(() => {
	mock.reset();
});

afterEach(() => {
	vi.clearAllTimers();
});

describe("AppointmentsPage", () => {
	it("renders page header and new appointment button", async () => {
		pushPage([]);
		render(<AppointmentsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Appointments")).toBeTruthy();
			expect(
				screen.getByRole("button", { name: /new appointment/i }),
			).toBeTruthy();
		});
	});

	it("renders scheduled appointments for the selected day", async () => {
		pushPage([appt1]);
		render(<AppointmentsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Screen replacement")).toBeTruthy();
		});
	});

	it("shows no-appointments message for empty day", async () => {
		pushPage([]);
		render(<AppointmentsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/no appointments this day/i)).toBeTruthy();
		});
	});

	it("opens the new appointment form", async () => {
		pushPage([]);
		render(<AppointmentsPage />, { wrapper });

		await waitFor(() => {
			expect(
				screen.getByRole("button", { name: /new appointment/i }),
			).toBeTruthy();
		});

		const newBtn = screen.getByRole("button", { name: /new appointment/i });
		await userEvent.click(newBtn);

		await waitFor(() => {
			expect(screen.getByText(/select customer/i)).toBeTruthy();
			expect(screen.getByPlaceholderText(/title/i)).toBeTruthy();
		});
	});
});
