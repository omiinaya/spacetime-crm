/**
 * Tests for PortalDashboard — greeting, stat cards, loading, and error handling.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import PortalDashboard from "@/pages/PortalDashboard";
import { PortalAuthProvider } from "@/lib/portal-auth";
import { mockFetch } from "../lib/mock-fetch";
import { Toaster } from "sonner";

const wrapper = ({ children }: { children: React.ReactNode }) => {
	return (
		<PortalAuthProvider>
			<Toaster />
			{children}
		</PortalAuthProvider>
	);
};

const mock = mockFetch();

const stats = {
	total_tickets: 5,
	open_tickets: 2,
	total_invoices: 4,
	total_billed: 800,
	total_paid: 300,
	balance_due: 500,
	upcoming_appointments: 1,
};

beforeEach(() => {
	mock.reset();
	localStorage.clear();
});

describe("PortalDashboard", () => {
	it("renders greeting with customer first name", () => {
		localStorage.setItem(
			"portal_token",
			"tok",
		);
		localStorage.setItem(
			"portal_customer",
			JSON.stringify({
				id: "cust_1",
				first_name: "Alice",
				last_name: "Smith",
				email: "a@b.com",
				company: "",
				phone: "",
			}),
		);
		mock.push(stats);
		render(<PortalDashboard />, { wrapper });

		expect(screen.getByText("Welcome, Alice!")).toBeTruthy();
	});

	it("renders stat cards from API", async () => {
		mock.push(stats);
		render(<PortalDashboard />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Open Tickets")).toBeTruthy();
		});
		expect(screen.getByText("2")).toBeTruthy();
		expect(screen.getByText("Total Invoices")).toBeTruthy();
		expect(screen.getByText("4")).toBeTruthy();
		expect(screen.getByText("Balance Due")).toBeTruthy();
		expect(screen.getByText("$500.00")).toBeTruthy();
		expect(screen.getByText("Upcoming Appts")).toBeTruthy();
		expect(screen.getByText("1")).toBeTruthy();
	});

	it("shows em-dash placeholders when stats missing", async () => {
		mock.push({});
		render(<PortalDashboard />, { wrapper });

		await waitFor(() => {
			expect(screen.getAllByText("—").length).toBeGreaterThan(0);
		});
	});

	it("shows error toast when stats fetch fails", async () => {
		mock.pushFail(500, "boom");
		render(<PortalDashboard />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Failed to load portal stats")).toBeTruthy();
		});
	});

	it("renders greeting without name when customer missing", () => {
		mock.push(stats);
		render(<PortalDashboard />, { wrapper });

		expect(screen.getByText("Welcome!")).toBeTruthy();
	});
});
