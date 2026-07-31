/**
 * Tests for GiftCardsPage — rendering, create, lookup, list, void.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GiftCardsPage from '@/pages/GiftCardsPage';
import { mockFetch, flushMicrotasks } from '../lib/mock-fetch';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { AuthProvider } from '@/lib/auth';

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

beforeEach(() => {
  mock.reset();
});

afterEach(() => {
  vi.clearAllTimers();
});

// ── Loading state ──

it('shows loading spinner while fetching', () => {
  // Don't push any response — stays loading
  const { container } = render(<GiftCardsPage />, { wrapper });
  const spinner = container.querySelector('.animate-spin');
  expect(spinner).toBeTruthy();
});

// ── Empty state ──

it('shows empty state when no gift cards exist', async () => {
  mock.push({ gift_cards: [], total: 0 }); // list
  render(<GiftCardsPage />, { wrapper });
  await waitFor(() => {
    expect(screen.getByText(/no gift cards/i)).toBeTruthy();
  });
});

// ── List gift cards ──

it('renders gift cards from the API', async () => {
  mock.push({
    gift_cards: [
      {
        id: 'gc_1',
        code: 'GC-ABCD1234EFGH',
        initial_balance: 100,
        remaining_balance: 75,
        active: true,
        customer_name: 'Alice',
        created_at: Date.now(),
      },
      {
        id: 'gc_2',
        code: 'GC-WXYZ5678IJKL',
        initial_balance: 50,
        remaining_balance: 0,
        active: true,
        customer_name: 'Bob',
        created_at: Date.now(),
      },
    ],
    total: 2,
  });

  render(<GiftCardsPage />, { wrapper });

  await waitFor(() => {
    expect(screen.getByText('GC-ABCD1234EFGH')).toBeTruthy();
    expect(screen.getByText('GC-WXYZ5678IJKL')).toBeTruthy();
    expect(screen.getByText('Alice')).toBeTruthy();
    expect(screen.getByText('Bob')).toBeTruthy();
  });
});

// ── Lookup form ──

it('shows lookup result after searching a code', async () => {
  // First call is the list query
  mock.push({ gift_cards: [], total: 0 });
  // Second call will be the lookup
  mock.push({
    gift_card: {
      id: 'gc_3',
      code: 'GC-LOOKUP',
      initial_balance: 200,
      remaining_balance: 150,
      active: true,
      customer_name: 'Charlie',
      created_at: Date.now(),
    },
  });

  render(<GiftCardsPage />, { wrapper });

  await waitFor(() => {
    expect(screen.getByText(/no gift cards/i)).toBeTruthy();
  });

  const input = screen.getByPlaceholderText(/enter gift card code/i);
  await userEvent.type(input, 'GC-LOOKUP');
  const lookupBtn = screen.getByRole('button', { name: /lookup/i });
  await userEvent.click(lookupBtn);

  await waitFor(() => {
    expect(screen.getByText('GC-LOOKUP')).toBeTruthy();
    expect(screen.getByText('$200.00')).toBeTruthy();
    expect(screen.getByText('$150.00')).toBeTruthy();
    expect(screen.getByText('Charlie')).toBeTruthy();
  });
});

// ─── Active filter toggle ──

it('shows active/voided filter buttons', async () => {
  mock.push({ gift_cards: [], total: 0 });

  render(<GiftCardsPage />, { wrapper });

  await waitFor(() => {
    expect(screen.getByText('Active')).toBeTruthy();
    expect(screen.getByText('Voided')).toBeTruthy();
    expect(screen.getByText('All')).toBeTruthy();
  });
});

// ── Create form toggle ──

it('toggles create form', async () => {
  mock.push({ gift_cards: [], total: 0 });

  render(<GiftCardsPage />, { wrapper });

  await waitFor(() => {
    expect(screen.getByText(/no gift cards/i)).toBeTruthy();
  });

  const createBtn = screen.getByRole('button', { name: /new gift card/i });
  await userEvent.click(createBtn);

  expect(screen.getByPlaceholderText(/0\.00/i)).toBeTruthy();
  expect(screen.getByPlaceholderText(/customer name/i)).toBeTruthy();
});
