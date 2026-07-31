/**
 * Tests for CustomersPage — rendering, search, create form, edit, delete.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CustomersPage from '@/pages/CustomersPage';
import { mockFetch } from '../lib/mock-fetch';
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

const customerAlice = {
  id: 'cust_1',
  first_name: 'Alice',
  last_name: 'Johnson',
  email: 'alice@example.com',
  phone: '+15551112222',
  mobile: '',
  company: 'Acme',
  balance: 25.5,
  created_at: Date.now(),
};

const customerBob = {
  id: 'cust_2',
  first_name: 'Bob',
  last_name: 'Smith',
  email: 'bob@example.com',
  phone: '',
  mobile: '+15553334444',
  company: '',
  balance: 0,
  created_at: Date.now(),
};

function pushCustomerList(customers: unknown[], total = customers.length) {
  mock.push({ customers, total, offset: 0, limit: 25 });
  mock.push({ duplicates: [], count: 0 });
}

beforeEach(() => {
  mock.reset();
});

afterEach(() => {
  vi.clearAllTimers();
});

describe('CustomersPage', () => {
  it('renders page header while loading', () => {
    render(<CustomersPage />, { wrapper });
    expect(screen.getByText(/manage your customer database/i)).toBeTruthy();
  });

  it('shows empty state when no customers exist', async () => {
    pushCustomerList([]);
    render(<CustomersPage />, { wrapper });
    await waitFor(() => {
      expect(screen.getByText(/manage your customer database/i)).toBeTruthy();
      expect(screen.getByText(/no customers yet/i)).toBeTruthy();
    });
  });

  it('renders customers from the API', async () => {
    pushCustomerList([customerAlice, customerBob]);
    render(<CustomersPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Alice Johnson')).toBeTruthy();
      expect(screen.getByText('Bob Smith')).toBeTruthy();
      expect(screen.getByText('alice@example.com')).toBeTruthy();
    });
  });

  it('searches customers when typing in search box', async () => {
    pushCustomerList([customerAlice, customerBob]);
    render(<CustomersPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Alice Johnson')).toBeTruthy();
    });

    const searchInput = screen.getByPlaceholderText(/search/i);
    await userEvent.type(searchInput, 'Bob');
    await waitFor(() => {
      const calls = mock.calls();
      expect(calls.some((c) => c.url.includes('search=Bob'))).toBeTruthy();
    });
  });

  it('opens create form and saves a new customer', async () => {
    pushCustomerList([]);
    // 3rd call: POST /customers (create)
    mock.push({ ok: true });

    render(<CustomersPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/no customers yet/i)).toBeTruthy();
    });

    const addBtn = screen.getByRole('button', { name: /add customer/i });
    await userEvent.click(addBtn);

    const firstName = screen.getByPlaceholderText(/first name/i);
    const lastName = screen.getByPlaceholderText(/last name/i);
    const email = screen.getByPlaceholderText(/email/i);
    await userEvent.type(firstName, 'New');
    await userEvent.type(lastName, 'Person');
    await userEvent.type(email, 'new@example.com');

    const saveBtn = screen.getByRole('button', { name: /^create$/i });
    await userEvent.click(saveBtn);

    await waitFor(() => {
      const calls = mock.calls();
      const post = calls.find((c) => c.init?.method === 'POST' && c.url.includes('/customers'));
      expect(post).toBeTruthy();
      const body = JSON.parse(String(post!.init!.body));
      expect(body.first_name).toBe('New');
      expect(body.last_name).toBe('Person');
    });
  });

  it('shows duplicate badge when duplicates exist', async () => {
    mock.push({ customers: [], total: 0, offset: 0, limit: 25 });
    mock.push({
      duplicates: [
        {
          field: 'email',
          value: 'alice@example.com',
          customers: [customerAlice, customerAlice],
        },
      ],
      count: 2,
    });
    render(<CustomersPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/2 duplicates found/i)).toBeTruthy();
    });
  });

  it('deletes a customer', async () => {
    pushCustomerList([customerAlice]);
    mock.push({ ok: true }); // DELETE

    render(<CustomersPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Alice Johnson')).toBeTruthy();
    });

    const deleteBtn = screen.getAllByRole('button', { name: /delete/i })[0];
    await userEvent.click(deleteBtn);

    await waitFor(() => {
      const calls = mock.calls();
      expect(
        calls.some((c) => c.init?.method === 'DELETE' && c.url.includes('/customers/cust_1')),
      ).toBeTruthy();
    });
  });
});
