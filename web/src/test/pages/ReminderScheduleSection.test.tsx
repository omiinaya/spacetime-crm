/**
 * Tests for ReminderScheduleSection — load, change interval, save.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ReminderScheduleSection from "@/pages/settings/ReminderScheduleSection";
import { mockFetch, flushMicrotasks } from "../lib/mock-fetch";
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

beforeEach(() => {
	mock.reset();
});

afterEach(() => {
	vi.clearAllTimers();
});

const CONFIG = (reminder_interval_days: number) => ({
	config: { revenue_target: 25000, reminder_interval_days },
});

describe("ReminderScheduleSection", () => {
	it("renders title and loads the configured interval", async () => {
		mock.push(CONFIG(7));
		render(<ReminderScheduleSection />, { wrapper });

		expect(screen.getByText(/Overdue Reminder Schedule/i)).toBeTruthy();

		await waitFor(() => {
			const select = screen.getByLabelText(
				/reminder interval/i,
			) as HTMLSelectElement;
			expect(select.value).toBe("7");
		});
	});

	it("defaults to 3 days when config has no interval", async () => {
		mock.push({ config: { revenue_target: 25000 } });
		render(<ReminderScheduleSection />, { wrapper });

		await waitFor(() => {
			const select = screen.getByLabelText(
				/reminder interval/i,
			) as HTMLSelectElement;
			expect(select.value).toBe("3");
		});
	});

	it("offers the admin-selectable options 1/3/7/14 days", async () => {
		mock.push(CONFIG(3));
		render(<ReminderScheduleSection />, { wrapper });

		await waitFor(() => {
			const select = screen.getByLabelText(
				/reminder interval/i,
			) as HTMLSelectElement;
			const options = Array.from(select.options).map((o) => o.value);
			expect(options).toEqual(["1", "3", "7", "14"]);
		});
	});

	it("saves the new interval via POST /settings/app", async () => {
		mock.push(CONFIG(3)); // initial get
		render(<ReminderScheduleSection />, { wrapper });

		// Wait for the fetch to finish so the select is enabled
		await waitFor(() => {
			const select = screen.getByLabelText(
				/reminder interval/i,
			) as HTMLSelectElement;
			expect(select.disabled).toBe(false);
		});

		// Change to 14 days and save
		await userEvent.selectOptions(
			screen.getByLabelText(/reminder interval/i),
			"14",
		);
		mock.push({ ok: true, ...CONFIG(14) }); // save response
		await userEvent.click(screen.getByRole("button", { name: /save/i }));

		await waitFor(() => {
			const calls = mock.calls();
			const saveCall = calls.find((c) => c.init?.method === "POST");
			expect(saveCall).toBeTruthy();
			expect(saveCall!.url).toContain("/settings/app");
			expect(JSON.parse(String(saveCall!.init?.body))).toEqual({
				reminder_interval_days: 14,
			});
		});
	});

	it("shows a success toast when saved", async () => {
		mock.push(CONFIG(3)); // initial get
		render(<ReminderScheduleSection />, { wrapper });

		await waitFor(() => {
			const select = screen.getByLabelText(
				/reminder interval/i,
			) as HTMLSelectElement;
			expect(select.disabled).toBe(false);
		});

		await userEvent.selectOptions(
			screen.getByLabelText(/reminder interval/i),
			"7",
		);
		mock.push({ ok: true, ...CONFIG(7) });
		await userEvent.click(screen.getByRole("button", { name: /save/i }));

		await waitFor(() => {
			expect(screen.getByText(/Reminder schedule updated/i)).toBeTruthy();
		});
	});

	it("shows an error toast when the save fails", async () => {
		mock.push(CONFIG(3)); // initial get
		render(<ReminderScheduleSection />, { wrapper });

		await waitFor(() => {
			const select = screen.getByLabelText(
				/reminder interval/i,
			) as HTMLSelectElement;
			expect(select.disabled).toBe(false);
		});

		await userEvent.selectOptions(
			screen.getByLabelText(/reminder interval/i),
			"7",
		);
		mock.pushFail(422, "validation error");
		await userEvent.click(screen.getByRole("button", { name: /save/i }));

		await waitFor(() => {
			expect(
				screen.getByText(/Failed to save reminder schedule/i),
			).toBeTruthy();
		});
	});

	it("does not clobber revenue_target when saving the interval", async () => {
		mock.push(CONFIG(3));
		render(<ReminderScheduleSection />, { wrapper });

		await waitFor(() => {
			const select = screen.getByLabelText(
				/reminder interval/i,
			) as HTMLSelectElement;
			expect(select.disabled).toBe(false);
		});

		await userEvent.selectOptions(
			screen.getByLabelText(/reminder interval/i),
			"1",
		);
		mock.push({ ok: true, ...CONFIG(1) });
		await userEvent.click(screen.getByRole("button", { name: /save/i }));

		await waitFor(() => {
			const calls = mock.calls();
			const saveCall = calls.find((c) => c.init?.method === "POST");
			const body = JSON.parse(String(saveCall!.init?.body));
			expect(body).toEqual({ reminder_interval_days: 1 });
			expect(body.revenue_target).toBeUndefined();
		});
	});
});
