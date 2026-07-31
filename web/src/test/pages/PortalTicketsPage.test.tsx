/**
 * Tests for PortalTicketsPage — ticket list, expand detail, add note,
 * and error handling.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PortalTicketsPage from "@/pages/PortalTicketsPage";
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

const tickets = [
	{
		id: "tkt_1",
		ticket_number: 1001,
		title: "Laptop won't boot",
		description: "Power light flashes",
		device_type: "laptop",
		device_model: "ThinkPad X1",
		status: "in_progress",
		priority: "high",
		assigned_name: "Carlos",
		created_at: 1700000000000,
		updated_at: 1700000000000,
	},
	{
		id: "tkt_2",
		ticket_number: 1002,
		title: "Screen replacement",
		description: "Cracked display",
		device_type: "phone",
		device_model: "Galaxy S24",
		status: "resolved",
		priority: "medium",
		assigned_name: "Maria",
		created_at: 1700000000000,
		updated_at: 1700000000000,
	},
];

const ticketDetail = {
	ticket: {
		...tickets[0],
		notes: [
			{
				id: "note_1",
				ticket_id: "tkt_1",
				author: "Carlos",
				content: "Diagnosed: dead battery",
				created_at: 1700000000000,
			},
		],
	},
};

beforeEach(() => {
	mock.reset();
	localStorage.clear();
});

describe("PortalTicketsPage", () => {
	it("renders ticket list", async () => {
		mock.push({ tickets });
		render(<PortalTicketsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Laptop won't boot")).toBeTruthy();
		});
		expect(screen.getByText("Screen replacement")).toBeTruthy();
		expect(screen.getByText(/ThinkPad X1/)).toBeTruthy();
	});

	it("shows status badges", async () => {
		mock.push({ tickets });
		render(<PortalTicketsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Laptop won't boot")).toBeTruthy();
		});
		expect(screen.getByText("in progress")).toBeTruthy();
		expect(screen.getByText("resolved")).toBeTruthy();
	});

	it("expands ticket to show notes", async () => {
		mock.push({ tickets });
		mock.push(ticketDetail); // GET /api/portal/tickets/tkt_1
		render(<PortalTicketsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Laptop won't boot")).toBeTruthy();
		});

		await userEvent.click(screen.getByText("Laptop won't boot"));

		await waitFor(() => {
			expect(screen.getByText("Diagnosed: dead battery")).toBeTruthy();
		});
	});

	it("adds a note to a ticket", async () => {
		mock.push({ tickets });
		mock.push(ticketDetail); // GET detail
		mock.push({ ok: true }); // POST note
		mock.push(ticketDetail); // reload detail
		render(<PortalTicketsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Laptop won't boot")).toBeTruthy();
		});

		await userEvent.click(screen.getByText("Laptop won't boot"));
		await waitFor(() => {
			expect(screen.getByText("Diagnosed: dead battery")).toBeTruthy();
		});

		await userEvent.type(
			screen.getByPlaceholderText(/add a note/i),
			"Please update me",
		);
		await userEvent.click(screen.getByText("Send"));

		await waitFor(() => {
			expect(mock.calls().some((c) => c.init?.method === "POST")).toBe(true);
		});
	});

	it("shows error toast when tickets fail to load", async () => {
		mock.pushFail(500, "boom");
		render(<PortalTicketsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Failed to load tickets")).toBeTruthy();
		});
	});

	it("shows empty state when no tickets", async () => {
		mock.push({ tickets: [] });
		render(<PortalTicketsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/no tickets/i)).toBeTruthy();
		});
	});
});
