import { renderHook, act } from '@testing-library/react';

const mockTriageIssue = vi.fn();
const mockShowSuccess = vi.fn();
const mockShowError = vi.fn();

vi.mock('../../api', () => ({
  triageIssue: (...args: unknown[]) => mockTriageIssue(...args),
}));

vi.mock('../../../../hooks/useToast', () => ({
  useToast: () => ({
    showSuccess: mockShowSuccess,
    showError: mockShowError,
  }),
}));

import { useTriageForm } from '../useTriageForm';

describe('useTriageForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('surfaces the underlying error message when triage fails', async () => {
    mockTriageIssue.mockRejectedValueOnce(new Error('Triage service unavailable'));

    const { result } = renderHook(() => useTriageForm());
    act(() => {
      result.current.setDescription('The app crashes on save.');
    });

    const e = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(async () => {
      await result.current.handleSubmit(e);
    });

    expect(result.current.error).toBe('Triage service unavailable');
    expect(mockShowError).toHaveBeenCalledWith('Triage failed', 'Triage service unavailable');
  });
});

