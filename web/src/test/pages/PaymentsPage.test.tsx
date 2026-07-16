/**
 * Smoke test for PaymentsPage - renders payment list
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "../test-utils";
import PaymentsPage from "@/pages/PaymentsPage";

vi.mock("@tanstack/react-query", async (importOriginal) => {
	const actual = await importOriginal();
	return {
		...actual,
		useQuery: vi
			.fn()
			.mockReturnValue({ data: { data: [], total: 0 }, isLoading: false }),
		useMutation: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
	};
});

vi.mock("@/lib/api", () => ({
	api: { payments: { list: vi.fn(), delete: vi.fn() } },
}));

vi.mock("@/lib/usePagination", () => ({
	usePagination: vi.fn().mockReturnValue({
		page: 1,
		totalPages: 0,
		total: 0,
		hasPrev: false,
		hasNext: false,
		prevPage: vi.fn(),
		nextPage: vi.fn(),
		goToPage: vi.fn(),
		offset: 0,
		setTotal: vi.fn(),
	}),
}));

describe("PaymentsPage", () => {
	it("renders the page", () => {
		render(<PaymentsPage />);
		expect(screen.getByText("Payments")).toBeInTheDocument();
	});
});
