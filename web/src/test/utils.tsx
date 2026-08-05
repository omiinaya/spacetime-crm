/**
 * Shared test utilities — a render wrapper that supplies a real
 * QueryClientProvider, so pages using react-query's useQuery/useMutation
 * can be rendered without "No QueryClient set" errors.
 */
import React from "react";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export function makeQueryClient() {
	return new QueryClient({
		defaultOptions: {
			queries: { retry: false },
			mutations: { retry: false },
		},
	});
}

export function renderWithQuery(ui: React.ReactElement) {
	const qc = makeQueryClient();
	return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}
