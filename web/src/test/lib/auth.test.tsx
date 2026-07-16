import { describe, it, expect } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { AuthProvider, useAuth, hasRole, authHeaders } from '@/lib/auth';

// Helper component that uses the auth context
function TestConsumer() {
  const auth = useAuth();
  return (
    <div>
      <span data-testid="loading">{auth.loading ? 'loading' : 'loaded'}</span>
      <span data-testid="user">{auth.user ? auth.user.email : 'null'}</span>
      <span data-testid="token">{auth.token ? 'has-token' : 'no-token'}</span>
    </div>
  );
}

describe('AuthProvider', () => {
  it('resolves to loaded with no user when no token stored', async () => {
    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    );

    // After initial render + effect, should be loaded with no user
    const loading = await screen.findByTestId('loading');
    expect(loading.textContent).toBe('loaded');
    expect(screen.getByTestId('user').textContent).toBe('null');
    expect(screen.getByTestId('token').textContent).toBe('no-token');
  });
});

describe('useAuth', () => {
  it('throws when used outside AuthProvider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<TestConsumer />)).toThrow('useAuth must be used within AuthProvider');
    spy.mockRestore();
  });
});

describe('hasRole', () => {
  it('returns false for null user', () => {
    expect(hasRole(null, 'admin')).toBe(false);
  });

  it('returns true if user has matching role', () => {
    expect(hasRole({ role: 'admin' }, 'admin')).toBe(true);
  });

  it('returns true if user has any of the given roles', () => {
    expect(hasRole({ role: 'tech' }, 'admin', 'tech', 'front_desk')).toBe(true);
  });

  it('returns false if user role does not match', () => {
    expect(hasRole({ role: 'front_desk' }, 'admin', 'tech')).toBe(false);
  });

  it('handles missing role field', () => {
    expect(hasRole({} as { role?: string }, 'admin')).toBe(false);
  });
});

describe('authHeaders', () => {
  it('returns empty object for null token', () => {
    expect(authHeaders(null)).toEqual({});
  });

  it('returns Authorization header for valid token', () => {
    const result = authHeaders('my-token');
    expect(result).toEqual({ Authorization: 'Bearer my-token' });
  });
});
