import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import BetaSignal from '../BetaSignal';

const mockSubmitBetaSignal = jest.fn();

jest.mock('next/navigation', () => ({
  usePathname: () => '/chat',
}));

jest.mock('@/lib/api', () => ({
  apiClient: {
    submitBetaSignal: (...args: unknown[]) => mockSubmitBetaSignal(...args),
  },
}));

describe('BetaSignal', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('captures optional participant identity with the confusion note', async () => {
    render(<BetaSignal />);

    fireEvent.click(screen.getByRole('button', { name: /report confusion/i }));
    fireEvent.change(screen.getByPlaceholderText(/name \(optional\)/i), {
      target: { value: 'Ava' },
    });
    fireEvent.change(screen.getByPlaceholderText(/email \(optional\)/i), {
      target: { value: 'ava@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: /which model am i using\?/i }));
    fireEvent.change(screen.getByPlaceholderText(/more detail\? \(optional\)/i), {
      target: { value: 'Wanted to verify the active model.' },
    });
    fireEvent.click(screen.getByRole('button', { name: /send/i }));

    await waitFor(() => {
      expect(mockSubmitBetaSignal).toHaveBeenCalledWith({
        page: '/chat',
        name: 'Ava',
        email: 'ava@example.com',
        note: 'Wanted to verify the active model.',
        tag: 'which-model',
      });
    });
  });
});
