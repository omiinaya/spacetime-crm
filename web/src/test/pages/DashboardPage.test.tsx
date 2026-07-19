/**
 * Smoke test for DashboardPage - renders with stats and navigation
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import DashboardPage from '@/pages/DashboardPage';

const defaultStats = {
  total_customers: 42,
  active_tickets: 7,
  unpaid_invoices: 3,
  total_revenue: 15000,
  appointments_today: [],
  page_stubs: [],
  tickets_by_status: [],
  invoices_by_status: [],
};

describe('DashboardPage', () => {
  it('renders basic stats in cards', () => {
    render(<DashboardPage stats={defaultStats} onNavigate={vi.fn()} />);
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('$15,000')).toBeInTheDocument();
  });
});
