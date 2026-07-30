import React from "react";
import {
  QueryClient,
  QueryClientProvider as Provider,
} from "@tanstack/react-query";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000, // 15s — refetch after inactivity
      retry: 2, // retry twice on failure
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 0, // don't retry mutations
    },
  },
});

export function QueryProvider({ children }: { children: React.ReactNode }) {
  return <Provider client={queryClient}>{children}</Provider>;
}

export { queryClient };
