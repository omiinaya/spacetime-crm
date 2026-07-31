/**
 * Tests for PortalAppointmentsPage — upcoming/past lists, status badges,
 * and error handling.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import PortalAppointmentsPage from "@/pages/PortalAppointmentsPage";
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

const appointmentsData = {
	appointments: [],
	upcoming: [
		{
			id: "apt_1",
			title: "Screen Replacement",
			description: "Bring your phone",
			start_time: 1750000000000,
			end_time: 1750003600000,
			status: "confirmed",
		},
	],
	past: [
		{
			id: "apt_2",
			title: "Battery Check",
			description: "Completed",
			start_time: 1700000000000,
			end_time: 1700003600000,
			status: "completed",
		},
	],
};

beforeEach(() => {
	mock.reset();
	localStorage.clear();
});

describe("PortalAppointmentsPage", () => {
	it("renders page header", async () => {
		mock.push(appointmentsData);
		render(<PortalAppointmentsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("My Appointments")).toBeTruthy();
		});
	});

	it("shows upcoming and past appointments", async () => {
		mock.push(appointmentsData);
		render(<PortalAppointmentsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Screen Replacement")).toBeTruthy();
		});
		expect(screen.getByText("Battery Check")).toBeTruthy();
	});

	it("shows status badges for appointments", async () => {
		mock.push(appointmentsData);
		render(<PortalAppointmentsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("confirmed")).toBeTruthy();
		});
		expect(screen.getByText("completed")).toBeTruthy();
	});

	it("shows error toast when loading fails", async () => {
		mock.pushFail(500, "boom");
		render(<PortalAppointmentsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Failed to load appointments")).toBeTruthy();
		});
	});

	it("shows empty state when no appointments", async () => {
		mock.push({ appointments: [], upcoming: [], past: [] });
		render(<PortalAppointmentsPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/no appointments/i)).toBeTruthy();
		});
	});
});
