/**
 * Tests for MapPage — location list rendering, geocode actions, and errors.
 * react-leaflet components are mocked (jsdom cannot render a real map).
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MapPage from "@/pages/MapPage";
import { mockFetch } from "../lib/mock-fetch";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { AuthProvider } from "@/lib/auth";

vi.mock("react-leaflet", () => ({
	MapContainer: ({ children }: { children: React.ReactNode }) => (
		<div data-testid="map">{children}</div>
	),
	TileLayer: () => null,
	Marker: ({ children }: { children: React.ReactNode }) => (
		<div>{children}</div>
	),
	Popup: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
	useMap: () => ({ fitBounds: vi.fn() }),
}));

vi.mock("leaflet", () => ({
	default: {
		Icon: { Default: { prototype: {}, mergeOptions: vi.fn() } },
		latLngBounds: () => ({ pad: () => ({}) }),
	},
	Icon: { Default: { prototype: {}, mergeOptions: vi.fn() } },
	latLngBounds: () => ({ pad: () => ({}) }),
}));

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

const locations = [
	{
		id: "cust_1",
		customer_id: "cust_1",
		name: "Alice Smith",
		latitude: 40.7128,
		longitude: -74.006,
		address: "New York, NY",
		updated_at: 1700000000000,
	},
	{
		id: "cust_2",
		customer_id: "cust_2",
		name: "Bob Jones",
		latitude: 34.0522,
		longitude: -118.2437,
		address: "Los Angeles, CA",
		updated_at: 1700000000000,
	},
];

beforeEach(() => {
	mock.reset();
	localStorage.clear();
});

describe("MapPage", () => {
	it("renders page header and map", async () => {
		mock.push({ locations });
		render(<MapPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Customer Map")).toBeTruthy();
		});
		expect(screen.getByTestId("map")).toBeTruthy();
	});

	it("shows customer locations list", async () => {
		mock.push({ locations });
		render(<MapPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("Alice Smith")).toBeTruthy();
		});
		expect(screen.getByText("Bob Jones")).toBeTruthy();
		expect(screen.getByText("New York, NY")).toBeTruthy();
		expect(screen.getByText("Los Angeles, CA")).toBeTruthy();
	});

	it("shows error when locations fail to load", async () => {
		mock.pushFail(500, "Server exploded");
		render(<MapPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText(/Server exploded/)).toBeTruthy();
		});
	});

	it("shows empty state when no geocoded customers", async () => {
		mock.push({ locations: [] });
		render(<MapPage />, { wrapper });

		await waitFor(() => {
			expect(screen.getByText("No customer locations yet")).toBeTruthy();
		});
	});
});
