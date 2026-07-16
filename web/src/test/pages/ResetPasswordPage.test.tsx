/**
 * Tests for ResetPasswordPage – token extraction, form validation,
 * password match, API submit, redirect on success.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ResetPasswordPage from "@/pages/ResetPasswordPage";

const { mockToastError, mockToastSuccess } = vi.hoisted(() => ({
	mockToastError: vi.fn(),
	mockToastSuccess: vi.fn(),
}));

vi.mock("sonner", () => ({
	toast: {
		error: (msg: string) => mockToastError(msg),
		success: (msg: string) => mockToastSuccess(msg),
	},
	Toaster: () => null,
}));

beforeEach(() => {
	mockToastError.mockReset();
	mockToastSuccess.mockReset();
	vi.restoreAllMocks();
});

afterEach(() => {
	vi.unstubAllGlobals();
});

// ── No-token state ──

it("shows invalid link state when no token in URL", () => {
	// Ensure no token param
	vi.stubGlobal(
		"URLSearchParams",
		class {
			constructor() {}
			get() {
				return null;
			}
			[Symbol.iterator]() {
				return [][Symbol.iterator]();
			}
		} as unknown as typeof URLSearchParams,
	);

	render(<ResetPasswordPage />);

	expect(screen.getByText("Invalid Reset Link")).toBeInTheDocument();
	expect(
		screen.getByText(/This password reset link is invalid/),
	).toBeInTheDocument();
	expect(screen.getByText("Request a new reset link")).toBeInTheDocument();
});

// ── Form rendering ──

it("renders the reset password form when token is present", async () => {
	vi.stubGlobal(
		"URLSearchParams",
		class {
			constructor() {}
			get(key: string) {
				return key === "token" ? "abc123" : null;
			}
			[Symbol.iterator]() {
				return [][Symbol.iterator]();
			}
		} as unknown as typeof URLSearchParams,
	);

	render(<ResetPasswordPage />);

	// Wait for the useEffect that reads the token ("Reset Password" appears in h1 + button)
	await waitFor(() => {
		expect(screen.getAllByText("Reset Password").length).toBeGreaterThan(0);
	});
	expect(screen.getByPlaceholderText("Enter new password")).toBeInTheDocument();
	expect(
		screen.getByPlaceholderText("Confirm new password"),
	).toBeInTheDocument();
	expect(
		screen.getByRole("button", { name: /reset password/i }),
	).toBeInTheDocument();
});

// ── Client-side validation ──

it("shows error when passwords don't match", async () => {
	vi.stubGlobal(
		"URLSearchParams",
		class {
			constructor() {}
			get(key: string) {
				return key === "token" ? "abc123" : null;
			}
			[Symbol.iterator]() {
				return [][Symbol.iterator]();
			}
		} as unknown as typeof URLSearchParams,
	);

	const user = userEvent.setup();
	render(<ResetPasswordPage />);

	await waitFor(() => screen.getByPlaceholderText("Enter new password"));
	await user.type(
		screen.getByPlaceholderText("Enter new password"),
		"password123",
	);
	await user.type(
		screen.getByPlaceholderText("Confirm new password"),
		"different",
	);
	await user.click(screen.getByRole("button", { name: /reset password/i }));

	expect(mockToastError).toHaveBeenCalledWith("Passwords do not match");
});

it("shows error when password is too short", async () => {
	vi.stubGlobal(
		"URLSearchParams",
		class {
			constructor() {}
			get(key: string) {
				return key === "token" ? "abc123" : null;
			}
			[Symbol.iterator]() {
				return [][Symbol.iterator]();
			}
		} as unknown as typeof URLSearchParams,
	);

	const user = userEvent.setup();
	render(<ResetPasswordPage />);

	await waitFor(() => screen.getByPlaceholderText("Enter new password"));
	await user.type(screen.getByPlaceholderText("Enter new password"), "12");
	await user.type(screen.getByPlaceholderText("Confirm new password"), "12");
	await user.click(screen.getByRole("button", { name: /reset password/i }));

	expect(mockToastError).toHaveBeenCalledWith(
		"Password must be at least 6 characters",
	);
});

// ── API call ──

it("submits password and token to the API", async () => {
	vi.stubGlobal(
		"URLSearchParams",
		class {
			constructor() {}
			get(key: string) {
				return key === "token" ? "abc123" : null;
			}
			[Symbol.iterator]() {
				return [][Symbol.iterator]();
			}
		} as unknown as typeof URLSearchParams,
	);

	const fetchSpy = vi.spyOn(window, "fetch").mockResolvedValueOnce(
		new Response("{}", {
			status: 200,
			headers: { "content-type": "application/json" },
		}),
	);

	const user = userEvent.setup();
	render(<ResetPasswordPage />);

	await waitFor(() => screen.getByPlaceholderText("Enter new password"));
	await user.type(
		screen.getByPlaceholderText("Enter new password"),
		"newpass123",
	);
	await user.type(
		screen.getByPlaceholderText("Confirm new password"),
		"newpass123",
	);
	await user.click(screen.getByRole("button", { name: /reset password/i }));

	await waitFor(() => {
		expect(fetchSpy).toHaveBeenCalledWith(
			"/api/auth/reset-password",
			expect.objectContaining({
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ token: "abc123", password: "newpass123" }),
			}),
		);
	});
});

it("shows success toast after successful reset", async () => {
	vi.stubGlobal(
		"URLSearchParams",
		class {
			constructor() {}
			get(key: string) {
				return key === "token" ? "abc123" : null;
			}
			[Symbol.iterator]() {
				return [][Symbol.iterator]();
			}
		} as unknown as typeof URLSearchParams,
	);

	vi.spyOn(window, "fetch").mockResolvedValueOnce(
		new Response("{}", {
			status: 200,
			headers: { "content-type": "application/json" },
		}),
	);

	const user = userEvent.setup();
	render(<ResetPasswordPage />);

	await waitFor(() => screen.getByPlaceholderText("Enter new password"));
	await user.type(
		screen.getByPlaceholderText("Enter new password"),
		"newpass123",
	);
	await user.type(
		screen.getByPlaceholderText("Confirm new password"),
		"newpass123",
	);
	await user.click(screen.getByRole("button", { name: /reset password/i }));

	await waitFor(() => {
		expect(mockToastSuccess).toHaveBeenCalledWith(
			expect.stringContaining("Password reset successfully"),
		);
	});
});

it("shows toast.error when API returns an error", async () => {
	vi.stubGlobal(
		"URLSearchParams",
		class {
			constructor() {}
			get(key: string) {
				return key === "token" ? "abc123" : null;
			}
			[Symbol.iterator]() {
				return [][Symbol.iterator]();
			}
		} as unknown as typeof URLSearchParams,
	);

	vi.spyOn(window, "fetch").mockResolvedValueOnce(
		new Response(JSON.stringify({ message: "Token expired" }), {
			status: 400,
			headers: { "content-type": "application/json" },
		}),
	);

	const user = userEvent.setup();
	render(<ResetPasswordPage />);

	await waitFor(() => screen.getByPlaceholderText("Enter new password"));
	await user.type(
		screen.getByPlaceholderText("Enter new password"),
		"newpass123",
	);
	await user.type(
		screen.getByPlaceholderText("Confirm new password"),
		"newpass123",
	);
	await user.click(screen.getByRole("button", { name: /reset password/i }));

	await waitFor(() => {
		expect(mockToastError).toHaveBeenCalledWith("Token expired");
	});
});

it("shows 'Resetting…' while request is in flight", async () => {
	vi.stubGlobal(
		"URLSearchParams",
		class {
			constructor() {}
			get(key: string) {
				return key === "token" ? "abc123" : null;
			}
			[Symbol.iterator]() {
				return [][Symbol.iterator]();
			}
		} as unknown as typeof URLSearchParams,
	);

	vi.spyOn(window, "fetch").mockReturnValueOnce(new Promise(() => {}));

	const user = userEvent.setup();
	render(<ResetPasswordPage />);

	await waitFor(() => screen.getByPlaceholderText("Enter new password"));
	await user.type(
		screen.getByPlaceholderText("Enter new password"),
		"newpass123",
	);
	await user.type(
		screen.getByPlaceholderText("Confirm new password"),
		"newpass123",
	);
	await user.click(screen.getByRole("button", { name: /reset password/i }));

	expect(screen.getByRole("button", { name: /resetting/i })).toBeDisabled();
});
