/**
 * Smoke test for PaymentsPage - renders payment list
 */
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import PaymentsPage from "@/pages/PaymentsPage";
import { renderWithQuery } from "../utils";

vi.mock("@/lib/api", () => ({
	api: { payments: { list: vi.fn(), delete: vi.fn() } },
}));

describe("PaymentsPage", () => {
	it("renders heading", () => {
		renderWithQuery(<PaymentsPage />);
		expect(screen.getAllByRole("heading").length).toBeGreaterThan(0);
	});
});
