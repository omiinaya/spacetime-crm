/**
 * Smoke test for SettingsPage - renders main sections
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import SettingsPage from "@/pages/SettingsPage";
import { renderWithQuery } from "../utils";

vi.mock("@/lib/api", () => ({
	api: { users: { list: vi.fn().mockResolvedValue({ data: [], total: 0 }) } },
}));

vi.mock("@/lib/auth", () => ({
	useAuth: () => ({
		user: { id: "u1", name: "Admin", role: "admin" },
		login: vi.fn(),
		logout: vi.fn(),
	}),
	AuthProvider: ({ children }: { children: React.ReactNode }) => (
		<>{children}</>
	),
	hasRole: () => true,
}));

describe("SettingsPage", () => {
	it("renders heading", () => {
		renderWithQuery(<SettingsPage />);
		expect(screen.getAllByRole("heading").length).toBeGreaterThan(0);
	});
});
