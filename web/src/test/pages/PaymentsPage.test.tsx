/**
 * Smoke test for PaymentsPage - renders payment list
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import PaymentsPage from '@/pages/PaymentsPage';

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn().mockReturnValue({ data: { data: [], total: 0 }, isLoading: false }),
  useMutation: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
}));

vi.mock('@/lib/api', () => ({
  api: { payments: { list: vi.fn(), delete: vi.fn() } },
}));

vi.mock('@/lib/usePagination', () => ({
  usePagination: vi.fn().mockReturnValue({
    page: 1, totalPages: 0, total: 0, hasPrev: false, hasNext: false,
    prevPage: vi.fn(), nextPage: vi.fn(), goToPage: vi.fn(), offset: 0,
  }),
}));

describe('PaymentsPage', () => {
  it('renders heading', () => {
    render(<PaymentsPage />);
    expect(screen.getByRole('heading')).toBeInTheDocument();
  });
});
