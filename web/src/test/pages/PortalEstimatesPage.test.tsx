/**
 * Tests for PortalEstimatesPage — estimate list, expand detail with line items,
 * and approve/decline actions.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PortalEstimatesPage from '@/pages/PortalEstimatesPage';
import { PortalAuthProvider } from '@/lib/portal-auth';
import { mockFetch } from '../lib/mock-fetch';
import { Toaster } from 'sonner';

const wrapper = ({ children }: { children: React.ReactNode }) => {
  return (
    <PortalAuthProvider>
      <Toaster />
      {children}
    </PortalAuthProvider>
  );
};

const mock = mockFetch();

const estimates = [
  {
    id: 'est_1',
    estimate_number: 1001,
    status: 'sent',
    subtotal: 200,
    tax_amount: 16,
    total: 216,
    discount_amount: 0,
    notes: 'Screen repair estimate',
    expires_at: 1705000000000,
    currency: 'USD',
    created_at: 1700000000000,
    line_items: [],
  },
  {
    id: 'est_2',
    estimate_number: 1002,
    status: 'approved',
    subtotal: 100,
    tax_amount: 8,
    total: 108,
    discount_amount: 0,
    notes: 'Battery',
    expires_at: 1705000000000,
    currency: 'USD',
    created_at: 1700000000000,
    line_items: [],
  },
];

const estDetail = {
  estimate: {
    ...estimates[0],
    line_items: [
      {
        id: 'li_1',
        description: 'Screen replacement',
        quantity: 1,
        unit_price: 200,
        total: 200,
      },
    ],
  },
};

beforeEach(() => {
  mock.reset();
  localStorage.clear();
});

describe('PortalEstimatesPage', () => {
  it('renders estimate list', async () => {
    mock.push({ estimates });
    render(<PortalEstimatesPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('My Estimates')).toBeTruthy();
    });
    await waitFor(() => {
      expect(screen.getByText('$216.00')).toBeTruthy();
    });
    expect(screen.getByText('$108.00')).toBeTruthy();
    expect(screen.getByText('#1001')).toBeTruthy();
  });

  it('shows estimate status badges', async () => {
    mock.push({ estimates });
    render(<PortalEstimatesPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Sent')).toBeTruthy();
    });
    expect(screen.getByText('Approved')).toBeTruthy();
  });

  it('expands estimate to show line items', async () => {
    mock.push({ estimates });
    mock.push(estDetail); // GET /api/portal/estimates/est_1
    render(<PortalEstimatesPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('#1001')).toBeTruthy();
    });

    await userEvent.click(screen.getByText('#1001'));

    await waitFor(() => {
      expect(screen.getByText('Screen replacement')).toBeTruthy();
    });
  });

  it('approves an estimate', async () => {
    mock.push({ estimates });
    mock.push(estDetail); // detail
    mock.push({ ok: true }); // POST status -> approved
    mock.push({ estimates: [{ ...estimates[0], status: 'approved' }, estimates[1]] }); // refresh list
    mock.push({
      estimate: { ...estimates[0], status: 'approved', line_items: [] },
    }); // refresh detail
    render(<PortalEstimatesPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('#1001')).toBeTruthy();
    });
    await userEvent.click(screen.getByText('#1001'));

    await waitFor(() => {
      expect(screen.getByText('Screen replacement')).toBeTruthy();
    });

    await userEvent.click(screen.getByText('Approve'));

    await waitFor(() => {
      expect(mock.calls().some((c) => c.url.includes('/estimates/est_1/status'))).toBe(true);
    });
  });

  it('declines an estimate', async () => {
    mock.push({ estimates });
    mock.push(estDetail);
    mock.push({ ok: true }); // POST status -> declined
    mock.push({ estimates: [{ ...estimates[0], status: 'declined' }, estimates[1]] });
    mock.push({
      estimate: { ...estimates[0], status: 'declined', line_items: [] },
    });
    render(<PortalEstimatesPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('#1001')).toBeTruthy();
    });
    await userEvent.click(screen.getByText('#1001'));

    await waitFor(() => {
      expect(screen.getByText('Screen replacement')).toBeTruthy();
    });

    await userEvent.click(screen.getByText('Decline'));

    await waitFor(() => {
      expect(
        mock
          .calls()
          .some(
            (c) =>
              c.url.includes('/estimates/est_1/status') &&
              JSON.parse(c.init?.body || '{}').status === 'declined',
          ),
      ).toBe(true);
    });
  });

  it('does not show approve/decline for already-decided estimates', async () => {
    mock.push({ estimates });
    mock.push({
      estimate: {
        ...estimates[1],
        line_items: [
          {
            id: 'li_2',
            description: 'Battery replacement',
            quantity: 1,
            unit_price: 100,
            total: 100,
          },
        ],
      },
    });
    render(<PortalEstimatesPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('#1002')).toBeTruthy();
    });
    await userEvent.click(screen.getByText('#1002'));

    await waitFor(() => {
      expect(screen.getByText('Battery replacement')).toBeTruthy();
    });

    expect(screen.queryByText('Approve')).toBeNull();
    expect(screen.queryByText('Decline')).toBeNull();
  });

  it('shows error toast when estimates fail to load', async () => {
    mock.pushFail(500, 'boom');
    render(<PortalEstimatesPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Failed to load estimates')).toBeTruthy();
    });
  });

  it('shows empty state when no estimates', async () => {
    mock.push({ estimates: [] });
    render(<PortalEstimatesPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/no estimates/i)).toBeTruthy();
    });
  });
});
