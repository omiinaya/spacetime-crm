/**
 * Tests for InvoicesPage — rendering, filters, new invoice form, bulk actions.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import InvoicesPage from '@/pages/InvoicesPage';
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

const invoice1 = {
  id: 'inv_1',
  invoice_number: 5001,
  tenant_id: 't1',
  customer_id: 'cust_1',
  status: 'sent',
  total: 199.99,
  paid: 0,
  due_date: Date.now() + 86400000,
  currency: 'USD',
  created_at: Date.now() - 86400000,
  updated_at: Date.now() - 86400000,
};

const invoice2 = {
  id: 'inv_2',
  invoice_number: 5002,
  tenant_id: 't1',
  customer_id: 'cust_1',
  status: 'paid',
  total: 50.0,
  paid: 50.0,
  due_date: 0,
  currency: 'USD',
  created_at: Date.now() - 172800000,
  updated_at: Date.now() - 172800000,
};

function pushPage(invoices: unknown[], total = invoices.length) {
  // Fetch order: summary query is defined first in InvoicesPage
  mock.push({
    by_status: {},
    total_count: total,
    total_revenue: 0,
    total_outstanding: 0,
    overdue_count: 0,
    overdue_total: 0,
  }); // invoice summary
  mock.push({ invoices, total, offset: 0, limit: 25 }); // invoices list
  mock.push({ customers: [customerAlice], total: 1, offset: 0, limit: 25 }); // customers
  mock.push({ tax_rates: [] }); // tax rates
}

beforeEach(() => {
  mock.reset();
});

afterEach(() => {
  vi.clearAllTimers();
});

describe('InvoicesPage', () => {
  it('renders page header and invoices from API', async () => {
    pushPage([invoice1, invoice2]);
    render(<InvoicesPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Invoices')).toBeTruthy();
      expect(screen.getByText('#5001')).toBeTruthy();
      expect(screen.getByText('#5002')).toBeTruthy();
    });
  });

  it('shows filter buttons', async () => {
    pushPage([]);
    render(<InvoicesPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /new invoice/i })).toBeTruthy();
    });
    expect(screen.getByRole('button', { name: /^All$/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /^paid$/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /^overdue$/i })).toBeTruthy();
  });

  it('opens the new invoice form', async () => {
    pushPage([]);
    render(<InvoicesPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /new invoice/i })).toBeTruthy();
    });

    const newBtn = screen.getByRole('button', { name: /new invoice/i });
    await userEvent.click(newBtn);

    await waitFor(() => {
      expect(screen.getByText(/select customer/i)).toBeTruthy();
      expect(screen.getByPlaceholderText(/notes/i)).toBeTruthy();
    });
  });

  it('creates a new invoice', async () => {
    pushPage([]);
    mock.push({ ok: true, id: 'inv_new' }); // POST /invoices

    render(<InvoicesPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /new invoice/i })).toBeTruthy();
    });

    const newBtn = screen.getByRole('button', { name: /new invoice/i });
    await userEvent.click(newBtn);

    // Select customer (first combobox)
    const comboboxes = screen.getAllByRole('combobox');
    await userEvent.selectOptions(comboboxes[0], 'cust_1');

    const notesInput = screen.getByPlaceholderText(/notes/i);
    await userEvent.type(notesInput, 'Rush repair');

    const createBtn = screen.getByRole('button', { name: /^create$/i });
    await userEvent.click(createBtn);

    await waitFor(() => {
      const calls = mock.calls();
      const post = calls.find((c) => c.init?.method === 'POST' && c.url.includes('/invoices'));
      expect(post).toBeTruthy();
      const body = JSON.parse(String(post!.init!.body));
      expect(body.customer_id).toBe('cust_1');
      expect(body.notes).toBe('Rush repair');
    });
  });

  it('selects invoices for bulk actions', async () => {
    pushPage([invoice1, invoice2]);
    render(<InvoicesPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('#5001')).toBeTruthy();
    });

    // Click the first invoice's select button
    const selectBtns = screen.getAllByRole('button');
    const selectBtn = selectBtns.find((b) => b.querySelector('svg')) as HTMLElement;
    await userEvent.click(selectBtn);
  });
});
