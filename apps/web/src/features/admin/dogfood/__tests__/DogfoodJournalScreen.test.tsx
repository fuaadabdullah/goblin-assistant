import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import type { DogfoodLogInput } from '@/lib/api';
import DogfoodJournalScreen from '../DogfoodJournalScreen';

const mockSubmitDogfoodLog = jest.fn();
const mockInvalidateQueries = jest.fn();
const mockWriteText = jest.fn().mockResolvedValue(undefined);

jest.mock('@/lib/api', () => ({
  apiClient: {
    getKpi: jest.fn(),
    submitDogfoodLog: (...args: unknown[]) => mockSubmitDogfoodLog(...args),
  },
}));

jest.mock('@tanstack/react-query', () => ({
  useQuery: jest.fn(() => ({
    data: {
      system: {
        dogfood: {
          total_entries: 2,
          recent_entries: [
            {
              entry_id: 'dogfood-1',
              primary_assistant: 'Goblin',
              external_ai: 'Claude',
              reason: 'Needed deeper web research',
              context: 'Wanted source links',
              recorded_at: '2026-08-18T12:00:00Z',
              source: 'dashboard',
            },
          ],
          reason_counts: {
            'needed deeper web research': 1,
            'coding context was not enough': 1,
          },
        },
      },
    },
    isLoading: false,
    isError: false,
    error: null,
  })),
  useQueryClient: jest.fn(() => ({
    invalidateQueries: mockInvalidateQueries,
  })),
}));

jest.mock('@/features/admin/kpi/KpiDashboard', () => ({
  DogfoodSection: ({
    data,
    onSubmit,
  }: {
    data: { total_entries: number };
    onSubmit: (payload: DogfoodLogInput) => Promise<void>;
  }) => (
    <div>
      <div data-testid="dogfood-section">{String(data.total_entries)}</div>
      <button
        type="button"
        onClick={() =>
          void onSubmit({
            primary_assistant: 'Goblin',
            external_ai: 'Claude',
            reason: 'Needed deeper web research',
            context: 'Wanted source links',
          })
        }
      >
        submit
      </button>
    </div>
  ),
}));

describe('DogfoodJournalScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: mockWriteText,
      },
    });
  });

  it('renders the dogfood journal and submits logs through the KPI endpoint', async () => {
    render(<DogfoodJournalScreen />);

    expect(screen.getByRole('heading', { name: /dogfood journal/i })).toBeInTheDocument();
    expect(screen.getByText(/entries this week/i)).toBeInTheDocument();
    expect(screen.getByTestId('dogfood-week-entries')).toHaveTextContent('2');
    expect(screen.getByText(/unique reasons/i)).toBeInTheDocument();
    expect(screen.getByTestId('dogfood-week-unique-reasons')).toHaveTextContent('2');
    expect(screen.getByText(/top reason/i)).toBeInTheDocument();
    expect(screen.getByTestId('dogfood-week-top-reason')).toHaveTextContent('needed deeper web research');
    expect(screen.getByTestId('dogfood-week-reason-breakdown')).toHaveTextContent(
      'needed deeper web research',
    );
    expect(screen.getByTestId('dogfood-week-reason-breakdown')).toHaveTextContent(
      'coding context was not enough',
    );
    expect(screen.getByTestId('dogfood-section')).toHaveTextContent('2');

    fireEvent.click(screen.getByRole('button', { name: /copy weekly digest/i }));

    await waitFor(() => {
      expect(mockWriteText).toHaveBeenCalledWith(
        expect.stringContaining('Reason breakdown:'),
      );
    });
    expect(screen.getByRole('button', { name: /digest copied/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => {
      expect(mockSubmitDogfoodLog).toHaveBeenCalledWith({
        primary_assistant: 'Goblin',
        external_ai: 'Claude',
        reason: 'Needed deeper web research',
        context: 'Wanted source links',
      });
    });
    expect(mockInvalidateQueries).toHaveBeenCalled();
  });
});
