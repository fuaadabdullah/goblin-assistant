import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import '@testing-library/jest-dom';
import DogfoodCaptureDialog from '../DogfoodCaptureDialog';

const mockSubmitDogfoodLog = jest.fn();
const mockShowSuccess = jest.fn();
const mockShowError = jest.fn();
const mockOnOpenChange = jest.fn();

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

jest.mock('@/lib/api', () => ({
  apiClient: {
    submitDogfoodLog: (...args) => mockSubmitDogfoodLog(...args),
  },
}));

jest.mock('../../../../contexts/ToastContext', () => ({
  useToast: () => ({
    showSuccess: mockShowSuccess,
    showError: mockShowError,
  }),
}));

describe('DogfoodCaptureDialog', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('submits a dogfood note and closes the dialog', async () => {
    mockSubmitDogfoodLog.mockResolvedValueOnce({ success: true, data: {} });

    renderWithClient(<DogfoodCaptureDialog open onOpenChange={mockOnOpenChange} />);

    fireEvent.change(screen.getByPlaceholderText('Claude'), {
      target: { value: 'Claude' },
    });
    fireEvent.change(screen.getByPlaceholderText('Needed deeper web research'), {
      target: { value: 'Needed deeper web research' },
    });
    fireEvent.change(screen.getByPlaceholderText('Optional extra context'), {
      target: { value: 'Web search was the blocker.' },
    });
    fireEvent.click(screen.getByRole('button', { name: /needed deeper web research/i }));
    fireEvent.click(screen.getByRole('button', { name: /save note/i }));

    await waitFor(() => {
      expect(mockSubmitDogfoodLog).toHaveBeenCalledWith({
        primary_assistant: 'Goblin',
        external_ai: 'Claude',
        reason: 'Needed deeper web research',
        context: 'Web search was the blocker.',
      });
    });
    expect(mockShowSuccess).toHaveBeenCalled();
    expect(mockOnOpenChange).toHaveBeenCalledWith(false);
  });

  it('requires an external AI and reason', async () => {
    renderWithClient(<DogfoodCaptureDialog open onOpenChange={mockOnOpenChange} />);

    fireEvent.click(screen.getByRole('button', { name: /save note/i }));

    await waitFor(() => {
      expect(mockShowError).toHaveBeenCalledWith(
        'Dogfood note needs a target and reason',
        'Fill in the external AI and why you switched.'
      );
    });
    expect(mockSubmitDogfoodLog).not.toHaveBeenCalled();
  });
});
