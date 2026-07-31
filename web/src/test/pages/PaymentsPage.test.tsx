/**
 * Tests for PaymentsPage — rendering, record form, delete.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PaymentsPage from '@/pages/PaymentsPage';
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
  due_date: 0,
  currency: 'USD',
  created_at: Date.now(),
  updated_at: Date.now(),
};

const payment1 = {
  id: 'pmt_1',
  invoice_id: 'inv_1',
  customer_id: 'cust_1',
  amount: 100.0,
  method: 'cash',
  currency: 'USD',
  created_at: Date.now() - 3600000,
};

function pushPage(payments: unknown[], total = payments.length) {
  mock.push({ payments, total, offset: 0, limit: 25 }); // payments
  mock.push({ invoices: [invoice1], total: 1, offset: 0, limit: 25 }); // invoices
  mock.push({ customers: [customerAlice], total: 1, offset: 0, limit: 25 }); // customers
}

beforeEach(() => {
  mock.reset();
});

afterEach(() => {
  vi.clearAllTimers();
});

describe('PaymentsPage', () => {
  it('renders page header and payments from API', async () => {
    pushPage([payment1]);
    render(<PaymentsPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Payments')).toBeTruthy();
      // Amount appears in the Total Collected card and the payment row
      expect(screen.getAllByText(/USD 100\.00/).length).toBeGreaterThanOrEqual(1);
    });
  });

  it('opens record payment form', async () => {
    pushPage([]);
    render(<PaymentsPage />, { wrapper });

    await waitFor(() => {
      expect(
        screen.getAllByRole('button', { name: /record payment/i }).length,
      ).toBeGreaterThanOrEqual(1);
    });

    const recordBtn = screen.getAllByRole('button', { name: /record payment/i })[0];
    await userEvent.click(recordBtn);

    await waitFor(() => {
      expect(screen.getByText(/select invoice/i)).toBeTruthy();
      expect(screen.getByPlaceholderText(/amount/i)).toBeTruthy();
    });
  });

  it('records a payment', async () => {
    pushPage([]);
    mock.push({ ok: true }); // POST /payments

    render(<PaymentsPage />, { wrapper });

    await waitFor(() => {
      expect(
        screen.getAllByRole('button', { name: /record payment/i }).length,
      ).toBeGreaterThanOrEqual(1);
    });

    const recordBtn = screen.getAllByRole('button', { name: /record payment/i })[0];
    await userEvent.click(recordBtn);

    // Select invoice
    const comboboxes = screen.getAllByRole('combobox');
    await userEvent.selectOptions(comboboxes[0], 'inv_1');

    // Amount
    const amountInput = screen.getByPlaceholderText(/amount/i);
    await userEvent.type(amountInput, '150');

    const submitBtn = screen.getByRole('button', { name: /^record$/i });
    await userEvent.click(submitBtn);

    await waitFor(() => {
      const calls = mock.calls();
      const post = calls.find((c) => c.init?.method === 'POST' && c.url.includes('/payments'));
      expect(post).toBeTruthy();
    });
  });

  it('deletes a payment', async () => {
    pushPage([payment1]);
    mock.push({ ok: true }); // DELETE

    render(<PaymentsPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getAllByText(/USD 100\.00/).length).toBeGreaterThanOrEqual(1);
    });

    const deleteBtns = screen.getAllByRole('button');
    const deleteBtn = deleteBtns.find(
      (b) => b.querySelector('svg') && b.querySelector('.text-destructive'),
    );
    if (deleteBtn) await userEvent.click(deleteBtn);

    await waitFor(() => {
      const calls = mock.calls();
      expect(
        calls.some((c) => c.init?.method === 'DELETE' && c.url.includes('/payments/pmt_1')),
      ).toBeTruthy();
    });
  });
});
