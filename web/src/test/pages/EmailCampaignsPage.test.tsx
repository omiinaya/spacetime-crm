/**
 * Tests for EmailCampaignsPage — compose, templates, test-send, filter.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EmailCampaignsPage from '@/pages/EmailCampaignsPage';
import { AuthProvider } from '@/lib/auth';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { mockFetch, flushMicrotasks } from '../lib/mock-fetch';

const mock = mockFetch();

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <AuthProvider>
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    </AuthProvider>
  );
};

beforeEach(() => {
  mock.reset();
});

afterEach(() => {
  vi.clearAllTimers();
});

// ── Page renders ──

it('renders the page title', () => {
  render(<EmailCampaignsPage />, { wrapper });
  expect(screen.getByText(/email campaigns/i)).toBeTruthy();
});

// ── Compose form ──

it('shows subject input and HTML body textarea', () => {
  render(<EmailCampaignsPage />, { wrapper });
  expect(screen.getByPlaceholderText(/email subject line/i)).toBeTruthy();
  expect(screen.getByPlaceholderText(/<h1>Hello.*name/i)).toBeTruthy();
});

// ── Template buttons ──

it('shows template buttons', () => {
  render(<EmailCampaignsPage />, { wrapper });

  expect(screen.getByText('Promotional Offer')).toBeTruthy();
  expect(screen.getByText('Service Reminder')).toBeTruthy();
  expect(screen.getByText('Seasonal Greeting')).toBeTruthy();
});

it('fills the body when a template is clicked', async () => {
  render(<EmailCampaignsPage />, { wrapper });

  const promoBtn = screen.getByText('Promotional Offer');
  await userEvent.click(promoBtn);

  const textarea = screen.getByPlaceholderText(/<h1>Hello.*name/i) as HTMLTextAreaElement;
  expect(textarea.value).toContain('Special Offer');
});

// ── Customer filter dropdown ──

it('shows customer filter dropdown', () => {
  render(<EmailCampaignsPage />, { wrapper });

  expect(screen.getByText('All customers with email')).toBeTruthy();
});

it('shows days input for recent filter', async () => {
  render(<EmailCampaignsPage />, { wrapper });

  const select = screen.getByRole('combobox');
  await userEvent.selectOptions(select, 'recent');

  expect(screen.getByText(/days since last ticket/i)).toBeTruthy();
});

// ── Test email input ──

it('shows test email input', () => {
  render(<EmailCampaignsPage />, { wrapper });

  expect(screen.getByPlaceholderText(/test@example.com/i)).toBeTruthy();
});

// ── Send blast button ──

it('shows send blast button', () => {
  render(<EmailCampaignsPage />, { wrapper });

  expect(screen.getByText('Send Blast')).toBeTruthy();
});

// ── Check template loads correctly ──

it('loads service reminder template', async () => {
  render(<EmailCampaignsPage />, { wrapper });

  await userEvent.click(screen.getByText('Service Reminder'));

  const textarea = screen.getByPlaceholderText(/<h1>Hello.*name/i) as HTMLTextAreaElement;
  expect(textarea.value).toContain('Service Reminder');
  expect(textarea.value).toContain('due for service');
});
