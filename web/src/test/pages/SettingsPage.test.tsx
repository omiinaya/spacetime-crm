/**
 * Smoke test for SettingsPage - renders main sections
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '../test-utils';
import SettingsPage from '@/pages/SettingsPage';

vi.mock('@tanstack/react-query', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useQuery: vi.fn().mockReturnValue({ data: [], isLoading: false }),
    useMutation: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
  };
});

vi.mock('@/lib/api', () => ({
  api: { users: { list: vi.fn().mockResolvedValue({ data: [], total: 0 }) } },
}));

vi.mock('@/lib/auth', () => ({
  useAuth: () => ({
    user: { id: '1', name: 'Admin', role: 'admin' },
    token: 'test',
    loading: false,
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  hasRole: () => true,
}));

vi.mock('@/lib/theme', () => ({
  useTheme: () => ({ theme: 'dark', toggleTheme: vi.fn() }),
}));

describe('SettingsPage', () => {
  it('renders the page', () => {
    render(<SettingsPage />);
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });
});
