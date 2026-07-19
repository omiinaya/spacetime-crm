/**
 * Smoke test for SettingsPage - renders main sections
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import SettingsPage from '@/pages/SettingsPage';

vi.mock('@/lib/api', () => ({
  api: { users: { list: vi.fn().mockResolvedValue({ data: [], total: 0 }) } },
}));

describe('SettingsPage', () => {
  it('renders heading', () => {
    render(<SettingsPage />);
    expect(screen.getByRole('heading')).toBeInTheDocument();
  });
});
