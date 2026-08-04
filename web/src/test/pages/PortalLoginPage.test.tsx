/**
 * Tests for PortalLoginPage — login form validation, successful login,
 * and error handling.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PortalLoginPage from "@/pages/PortalLoginPage";
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

const loginResponse = {
	token: "portal_jwt_token",
	customer: {
		id: "cust_1",
		first_name: "Alice",
		last_name: "Smith",
		email: "alice@example.com",
		company: "",
		phone: "",
	},
};

beforeEach(() => {
	mock.reset();
	localStorage.clear();
});

describe("PortalLoginPage", () => {
	it("renders the portal login form", () => {
		render(<PortalLoginPage onSuccess={vi.fn()} />, { wrapper });

		expect(screen.getByText("Customer Portal")).toBeTruthy();
		expect(screen.getByPlaceholderText("Email")).toBeTruthy();
		expect(screen.getByPlaceholderText("Password")).toBeTruthy();
		expect(screen.getByText("Sign In")).toBeTruthy();
	});

	it("shows error when fields are empty", async () => {
		render(<PortalLoginPage onSuccess={vi.fn()} />, { wrapper });

		await userEvent.click(screen.getByText("Sign In"));

		await waitFor(() => {
			expect(screen.getByText("Email and password required")).toBeTruthy();
		});
	});

	it("logs in successfully and calls onSuccess", async () => {
		mock.push(loginResponse);
		const onSuccess = vi.fn();
		render(<PortalLoginPage onSuccess={onSuccess} />, { wrapper });

		await userEvent.type(
			screen.getByPlaceholderText("Email"),
			"alice@example.com",
		);
		await userEvent.type(screen.getByPlaceholderText("Password"), "secret123");
		await userEvent.click(screen.getByText("Sign In"));

		await waitFor(() => {
			expect(onSuccess).toHaveBeenCalled();
		});
		// Token + customer persisted
		expect(localStorage.getItem("portal_token")).toBe("portal_jwt_token");
	});

	it("shows error toast on invalid credentials", async () => {
		mock.pushFail(401, "Invalid credentials");
		render(<PortalLoginPage onSuccess={vi.fn()} />, { wrapper });

		await userEvent.type(
			screen.getByPlaceholderText("Email"),
			"alice@example.com",
		);
		await userEvent.type(screen.getByPlaceholderText("Password"), "wrong");
		await userEvent.click(screen.getByText("Sign In"));

		await waitFor(() => {
			expect(screen.getByText("Invalid email or password")).toBeTruthy();
		});
		expect(localStorage.getItem("portal_token")).toBeNull();
	});

	it("submits on Enter key", async () => {
		mock.push(loginResponse);
		const onSuccess = vi.fn();
		render(<PortalLoginPage onSuccess={onSuccess} />, { wrapper });

		await userEvent.type(
			screen.getByPlaceholderText("Email"),
			"alice@example.com",
		);
		await userEvent.type(screen.getByPlaceholderText("Password"), "secret123");
		await userEvent.type(screen.getByPlaceholderText("Password"), "{Enter}");

		await waitFor(() => {
			expect(onSuccess).toHaveBeenCalled();
		});
	});
});
