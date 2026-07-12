/**
 * Tests for LoginPage – form rendering, input validation, login flow,
 * error display, and "Forgot password?" link.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LoginPage from '@/pages/LoginPage';

// Mock the auth module so useAuth() gives us a controlled login function
const mockLogin = vi.fn();
vi.mock('@/lib/auth', () => ({
  useAuth: () => ({ login: mockLogin }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  hasRole: () => true,
}));

beforeEach(() => {
  mockLogin.mockReset();
});

// ── Basic rendering ──

it('renders the login page with brand and form', () => {
  render(<LoginPage />);

  expect(screen.getByText('SpacetimeCRM')).toBeInTheDocument();
  expect(screen.getByText('Sign in to your account')).toBeInTheDocument();
  expect(screen.getByPlaceholderText('admin@repairshop.com')).toBeInTheDocument();
  expect(screen.getByPlaceholderText('Enter your password')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
});

it("renders the 'Forgot password?' link", () => {
  render(<LoginPage />);
  const link = screen.getByText('Forgot password?');
  expect(link).toBeInTheDocument();
  expect(link.closest('a')).toHaveAttribute('href', '/forgot-password');
});

// ── Form interaction ──

it('calls login with email and password on submit', async () => {
  const user = userEvent.setup();
  render(<LoginPage />);

  await user.type(screen.getByPlaceholderText('admin@repairshop.com'), 'test@example.com');
  await user.type(screen.getByPlaceholderText('Enter your password'), 'mypassword');
  await user.click(screen.getByRole('button', { name: /sign in/i }));

  expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'mypassword');
});

it("shows 'Signing in…' while login is in progress", async () => {
  // Don't resolve the promise so we stay in loading state
  mockLogin.mockReturnValue(new Promise(() => {}));

  const user = userEvent.setup();
  render(<LoginPage />);

  await user.type(screen.getByPlaceholderText('admin@repairshop.com'), 'a@b.com');
  await user.type(screen.getByPlaceholderText('Enter your password'), 'pass123');
  await user.click(screen.getByRole('button', { name: /sign in/i }));

  expect(screen.getByRole('button', { name: /signing in/i })).toBeInTheDocument();
});

it('disables submit button while loading', async () => {
  mockLogin.mockReturnValue(new Promise(() => {}));

  const user = userEvent.setup();
  render(<LoginPage />);

  await user.type(screen.getByPlaceholderText('admin@repairshop.com'), 'a@b.com');
  await user.type(screen.getByPlaceholderText('Enter your password'), 'pass123');
  await user.click(screen.getByRole('button', { name: /sign in/i }));

  expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled();
});

// ── Error handling ──

it('shows error message when login fails', async () => {
  mockLogin.mockRejectedValue(new Error('Invalid credentials'));

  const user = userEvent.setup();
  render(<LoginPage />);

  await user.type(screen.getByPlaceholderText('admin@repairshop.com'), 'bad@user.com');
  await user.type(screen.getByPlaceholderText('Enter your password'), 'wrongpass');
  await user.click(screen.getByRole('button', { name: /sign in/i }));

  await waitFor(() => {
    expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
  });
});

it('shows generic error when login throws a non-Error', async () => {
  mockLogin.mockRejectedValue('Network error string');

  const user = userEvent.setup();
  render(<LoginPage />);

  await user.type(screen.getByPlaceholderText('admin@repairshop.com'), 'a@b.com');
  await user.type(screen.getByPlaceholderText('Enter your password'), 'pass');
  await user.click(screen.getByRole('button', { name: /sign in/i }));

  await waitFor(() => {
    expect(screen.getByText('Login failed')).toBeInTheDocument();
  });
});
