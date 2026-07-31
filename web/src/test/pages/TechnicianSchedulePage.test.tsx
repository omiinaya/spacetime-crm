/**
 * Tests for TechnicianSchedulePage — month navigation, tech selector,
 * per-tech summary cards, and grouped appointment rendering.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TechnicianSchedulePage from "@/pages/TechnicianSchedulePage";
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

const users = {
	users: [
		{ id: "u_1", name: "Carlos Tech", role: "tech", active: true },
		{ id: "u_2", name: "Admin User", role: "admin", active: true },
		{ id: "u_3", name: "Front Desk", role: "front_desk", active: true },
	],
	total: 3,
};

const byTech = {
	groups: [
		{
			user_id: "u_1",
			user_name: "Carlos Tech",
			appointments: [
				{
					id: "apt_1",
					title: "Laptop Repair",
					customer_name: "Alice",
					start_time: 1750000000000,
					end_time: 1750003600000,
					status: "confirmed",
					technician_id: "u_1",
				},
				{
					id: "apt_2",
					title: "Phone Screen",
					customer_name: "Bob",
					start_time: 1750007200000,
					end_time: 1750010800000,
					status: "scheduled",
					technician_id: "u_1",
				},
			],
		},
		{
			user_id: "u_2",
			user_name: "Admin User",
			appointments: [
				{
					id: "apt_3",
					title: "Server Check",
					customer_name: "Corp Inc",
					start_time: 1750000000000,
					end_time: 1750003600000,
					status: "in progress",
					technician_id: "u_2",
				},
			],
		},
	],
	unassigned: [],
};

function pushPage() {
	mock.push(users); // /api/users
	mock.push(byTech); // /api/appointments/by-tech?start=..&end=..
}

beforeEach(() => {
	mock.reset();
});

describe("TechnicianSchedulePage", () => {
	it("renders page header and month label", async () => {
		pushPage();
		render(<TechnicianSchedulePage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Technician Schedule")).toBeTruthy();
		});
		// Month label in format "July 2026"
		const now = new Date();
		const monthLabel = now.toLocaleDateString([], {
			month: "long",
			year: "numeric",
		});
		expect(screen.getByText(monthLabel)).toBeTruthy();
	});

	it("shows per-tech summary cards when no tech selected", async () => {
		pushPage();
		render(<TechnicianSchedulePage />, { wrapper });

		await waitFor(() => {
			expect(screen.getAllByText("Carlos Tech").length).toBeGreaterThan(0);
		});
		expect(screen.getAllByText("Admin User").length).toBeGreaterThan(0);
		// Front desk user filtered out of the tech selector options
		expect(screen.queryByText("Front Desk")).toBeNull();
		// Summary line: 3 appointment(s) across 2 tech(s)
		expect(screen.getByText(/3 appointment\(s\) across 2 tech\(s\)/)).toBeTruthy();
	});

	it("filters appointments when a tech is selected", async () => {
		pushPage();
		render(<TechnicianSchedulePage />, { wrapper });

		await waitFor(() => {
			expect(screen.getAllByText("Carlos Tech").length).toBeGreaterThan(0);
		});

		await userEvent.selectOptions(screen.getByRole("combobox"), "u_1");

		await waitFor(() => {
			expect(screen.getByText("Laptop Repair")).toBeTruthy();
		});
		expect(screen.getByText("Phone Screen")).toBeTruthy();
		// Admin's appointment hidden
		expect(screen.queryByText("Server Check")).toBeNull();
		// Summary: 2 appointment(s)
		expect(screen.getByText(/2 appointment\(s\)/)).toBeTruthy();
	});

	it("renders appointment status badges", async () => {
		pushPage();
		render(<TechnicianSchedulePage />, { wrapper });

		await waitFor(() => {
			expect(screen.getAllByText("Carlos Tech").length).toBeGreaterThan(0);
		});

		await userEvent.selectOptions(screen.getByRole("combobox"), "u_1");

		await waitFor(() => {
			expect(screen.getByText("Laptop Repair")).toBeTruthy();
		});
		expect(screen.getByText("confirmed")).toBeTruthy();
		expect(screen.getByText("scheduled")).toBeTruthy();
	});

	it("shows unassigned appointments count", async () => {
		mock.push(users);
		mock.push({
			groups: [],
			unassigned: [
				{
					id: "apt_9",
					title: "Walk-in",
					customer_name: "Walk In",
					start_time: 1750000000000,
					end_time: 1750003600000,
					status: "scheduled",
					technician_id: "",
				},
			],
		});
		render(<TechnicianSchedulePage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/1 unassigned/)).toBeTruthy();
		});
	});

	it("navigates months with next/prev buttons", async () => {
		pushPage();
		render(<TechnicianSchedulePage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Technician Schedule")).toBeTruthy();
		});

		// Capture the current month label, then click next.
		const monthSpan = screen.getByText(
			new Date()
				.toLocaleDateString([], { month: "long", year: "numeric" })
				.toString(),
		);
		const currentLabel = monthSpan.textContent ?? "";

		// Buttons: [0] = prev chevron, [1] = next chevron
		const buttons = screen.getAllByRole("button");
		await userEvent.click(buttons[1]);

		// After navigation the old label must be gone (replaced by next month).
		await waitFor(() => {
			expect(screen.queryByText(currentLabel)).toBeNull();
		});

		// "This Month" button appears when not on current month
		expect(screen.getByText("This Month")).toBeTruthy();
	});
});
