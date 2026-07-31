/**
 * Tests for PosPage — rendering, payment method selection, gift card sell.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PosPage from "@/pages/PosPage";
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

// Fake JWT with a valid payload for the AuthProvider
const fakeToken =
	"header." +
	btoa(
		JSON.stringify({
			sub: "user_1",
			name: "Test User",
			email: "test@example.com",
			role: "admin",
			tenant_id: "tenant_1",
		}),
	) +
	".sig";

beforeEach(() => {
	mock.reset();
	localStorage.setItem("crm_token", fakeToken);
});

afterEach(() => {
	vi.clearAllTimers();
	localStorage.removeItem("crm_token");
});

function pushPage() {
	// /api/auth/me → has_pin false → POS shows without PIN gate
	mock.push({ id: "user_1", has_pin: false });
	mock.push({ receipts: [], total: 0 }); // sales history
}

describe("PosPage", () => {
	it("renders page header and POS actions", async () => {
		pushPage();
		render(<PosPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Point of Sale")).toBeTruthy();
		});
	});

	it("shows payment method buttons", async () => {
		pushPage();
		render(<PosPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Point of Sale")).toBeTruthy();
		});
		expect(screen.getByRole("button", { name: "Cash" })).toBeTruthy();
		expect(screen.getByRole("button", { name: "Card" })).toBeTruthy();
		expect(screen.getByRole("button", { name: "Gift" })).toBeTruthy();
	});

	it("toggles the sell gift card panel", async () => {
		pushPage();
		render(<PosPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Point of Sale")).toBeTruthy();
		});

		const sellBtn = screen.getByRole("button", { name: /sell gift card/i });
		await userEvent.click(sellBtn);

		await waitFor(() => {
			expect(screen.getByText(/sell a gift card/i)).toBeTruthy();
		});
	});

	it("selects gift card as payment method", async () => {
		pushPage();
		render(<PosPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Point of Sale")).toBeTruthy();
		});

		const giftBtn = screen.getByRole("button", { name: "Gift" });
		await userEvent.click(giftBtn);

		await waitFor(() => {
			// Gift card payment panel should appear with a code input
			expect(screen.getByPlaceholderText(/gift card code/i)).toBeTruthy();
		});
	});
});
