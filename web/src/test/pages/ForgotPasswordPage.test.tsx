/**
 * Tests for ForgotPasswordPage – form validation, success state, API errors.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ForgotPasswordPage from '@/pages/ForgotPasswordPage';

// Hoisted before vi.mock so the factory can reference them
const { mockToastError, mockToastSuccess } = vi.hoisted(() => ({
  mockToastError: vi.fn(),
  mockToastSuccess: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    error: (msg: string) => mockToastError(msg),
    success: (msg: string) => mockToastSuccess(msg),
  },
  Toaster: () => null,
}));

beforeEach(() => {
  mockToastError.mockReset();
  mockToastSuccess.mockReset();
  vi.restoreAllMocks();
});

// ── Rendering ──

it('renders the forgot password page with brand and form', () => {
  render(<ForgotPasswordPage />);

  expect(screen.getByText('Forgot Password')).toBeInTheDocument();
  expect(screen.getByText('Enter your email to receive a reset link')).toBeInTheDocument();
  expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /send reset link/i })).toBeInTheDocument();
  expect(screen.getByText('Back to Login')).toBeInTheDocument();
});

// ── Client-side validation ──

it('shows inline error for empty email', async () => {
  const user = userEvent.setup();
  render(<ForgotPasswordPage />);

  // Type and clear to make input dirty, then submit via the form element
  const form = screen.getByRole('button', { name: /send reset link/i }).closest('form')!;
  fireEvent.submit(form);

  expect(screen.getByText('Please enter a valid email address.')).toBeInTheDocument();
});

it('shows inline error for invalid email format', async () => {
  const user = userEvent.setup();
  render(<ForgotPasswordPage />);

  await user.type(screen.getByPlaceholderText('you@example.com'), 'notanemail');
  const form = screen.getByRole('button', { name: /send reset link/i }).closest('form')!;
  fireEvent.submit(form);

  expect(screen.getByText('Please enter a valid email address.')).toBeInTheDocument();
});

// ── API call ──

it('calls forgot-password API with the email', async () => {
  const fetchSpy = vi.spyOn(window, 'fetch').mockResolvedValueOnce(
    new Response('{}', {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }),
  );

  const user = userEvent.setup();
  render(<ForgotPasswordPage />);

  await user.type(screen.getByPlaceholderText('you@example.com'), 'test@example.com');
  await user.click(screen.getByRole('button', { name: /send reset link/i }));

  await waitFor(() => {
    expect(fetchSpy).toHaveBeenCalledWith(
      '/api/auth/forgot-password',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ email: 'test@example.com' }),
      }),
    );
  });
});

it('shows success state when API responds ok', async () => {
  vi.spyOn(window, 'fetch').mockResolvedValueOnce(
    new Response('{}', {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }),
  );

  const user = userEvent.setup();
  render(<ForgotPasswordPage />);

  await user.type(screen.getByPlaceholderText('you@example.com'), 'test@example.com');
  await user.click(screen.getByRole('button', { name: /send reset link/i }));

  await waitFor(() => {
    expect(screen.getByText(/If that email exists/)).toBeInTheDocument();
  });
});

it('calls toast.error when API returns an error', async () => {
  vi.spyOn(window, 'fetch').mockResolvedValueOnce(new Response('Rate limited', { status: 400 }));

  const user = userEvent.setup();
  render(<ForgotPasswordPage />);

  await user.type(screen.getByPlaceholderText('you@example.com'), 'test@example.com');
  await user.click(screen.getByRole('button', { name: /send reset link/i }));

  await waitFor(() => {
    expect(mockToastError).toHaveBeenCalled();
  });
});

it("shows 'Sending…' while request is in flight", async () => {
  vi.spyOn(window, 'fetch').mockReturnValueOnce(new Promise(() => {}));

  const user = userEvent.setup();
  render(<ForgotPasswordPage />);

  await user.type(screen.getByPlaceholderText('you@example.com'), 'test@example.com');
  await user.click(screen.getByRole('button', { name: /send reset link/i }));

  expect(screen.getByRole('button', { name: /sending/i })).toBeDisabled();
});
