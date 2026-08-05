import { useState, useCallback } from "react";

interface PaginationState {
	offset: number;
	limit: number;
	total: number;
}

interface UsePaginationReturn {
	offset: number;
	limit: number;
	total: number;
	page: number;
	totalPages: number;
	hasNext: boolean;
	hasPrev: boolean;
	nextPage: () => void;
	prevPage: () => void;
	goToPage: (page: number) => void;
	setTotal: (total: number) => void;
	reset: () => void;
}

export function usePagination(initialLimit: number = 25): UsePaginationReturn {
	const [state, setState] = useState<PaginationState>({
		offset: 0,
		limit: initialLimit,
		total: 0,
	});

	const page = state.limit > 0 ? Math.floor(state.offset / state.limit) + 1 : 1;
	const totalPages =
		state.limit > 0 ? Math.max(1, Math.ceil(state.total / state.limit)) : 1;
	const hasNext = state.offset + state.limit < state.total;
	const hasPrev = state.offset > 0;

	const nextPage = useCallback(() => {
		setState((s) => ({
			...s,
			offset: s.offset + s.limit,
		}));
	}, []);

	const prevPage = useCallback(() => {
		setState((s) => ({
			...s,
			offset: Math.max(0, s.offset - s.limit),
		}));
	}, []);

	const goToPage = useCallback((p: number) => {
		setState((s) => ({
			...s,
			offset: Math.max(0, (p - 1) * s.limit),
		}));
	}, []);

	const setTotal = useCallback((total: number) => {
		setState((s) => ({ ...s, total }));
	}, []);

	const reset = useCallback(() => {
		setState((s) => ({ ...s, offset: 0 }));
	}, []);

	return {
		offset: state.offset,
		limit: state.limit,
		total: state.total,
		page,
		totalPages,
		hasNext,
		hasPrev,
		nextPage,
		prevPage,
		goToPage,
		setTotal,
		reset,
	};
}
