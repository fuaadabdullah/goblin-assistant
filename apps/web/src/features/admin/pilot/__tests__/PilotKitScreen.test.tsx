import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import PilotKitScreen from '../PilotKitScreen';

const mockWriteText = jest.fn().mockResolvedValue(undefined);
const mockGetKpi = jest.fn();

jest.mock('@tanstack/react-query', () => ({
  useQuery: jest.fn(() => ({
    data: {
      product: {
        pilot_signals: {
          total_signals: 1,
          unique_participants: 1,
          top_tags: [{ tag: 'which-model', count: 1 }],
          recent_signals: [
            {
              ticket_id: 'beta-1',
              name: 'Ava',
              email: 'ava@example.com',
              tag: 'which-model',
              note: 'Wanted to verify the active model.',
              created_at: '2026-08-18T12:00:00Z',
              page: '/chat',
            },
          ],
        },
      },
    },
    isLoading: false,
    isError: false,
    error: null,
  })),
}));

jest.mock('@/lib/api', () => ({
  apiClient: {
    getKpi: (...args: unknown[]) => mockGetKpi(...args),
  },
}));

describe('PilotKitScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetKpi.mockResolvedValue({
      product: {
        pilot_signals: {
          total_signals: 1,
          unique_participants: 1,
          top_tags: [{ tag: 'which-model', count: 1 }],
          recent_signals: [
            {
              ticket_id: 'beta-1',
              name: 'Ava',
              email: 'ava@example.com',
              tag: 'which-model',
              note: 'Wanted to verify the active model.',
              created_at: '2026-08-18T12:00:00Z',
              page: '/chat',
            },
          ],
        },
      },
    });
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: mockWriteText,
      },
    });
  });

  it('renders the pilot kit and copies the invite', async () => {
    render(<PilotKitScreen />);

    expect(screen.getByRole('heading', { name: /5-10 human pilot/i })).toBeInTheDocument();
    expect(screen.getAllByText(/what is a goblin\?/i)).toHaveLength(2);
    expect(screen.getAllByText(/what makes this better than chatgpt/i)).toHaveLength(3);
    expect(screen.getByText(/pilot roster/i)).toBeInTheDocument();
    expect(screen.getByText(/ava@example.com/i)).toBeInTheDocument();
    expect(screen.getByText(/wanted to verify the active model\./i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /copy invite/i }));

    await waitFor(() => {
      expect(mockWriteText).toHaveBeenCalledWith(
        expect.stringContaining('Try Goblin for 10 minutes'),
      );
    });

    expect(screen.getByRole('button', { name: /invite copied/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /copy pilot packet/i }));

    await waitFor(() => {
      expect(mockWriteText).toHaveBeenCalledWith(
        expect.stringContaining('# Goblin pilot packet'),
      );
    });
    expect(screen.getByRole('button', { name: /packet copied/i })).toBeInTheDocument();
  });
});
