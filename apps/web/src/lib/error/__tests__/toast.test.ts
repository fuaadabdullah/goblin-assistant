const { mockLogError, mockHandleError } = vi.hoisted(() => ({
  mockLogError: vi.fn(),
  mockHandleError: vi.fn(),
}));

vi.mock('../logger', () => ({
  logError: mockLogError,
}));

vi.mock('../handler', () => ({
  handleError: mockHandleError,
}));

import { getUserMessage, makeMutationErrorHandler, toastError } from '../toast';

describe('toast helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('uses warning toasts when the logged error is a warning', () => {
    const showError = vi.fn();
    const showWarning = vi.fn();
    mockLogError.mockReturnValue({
      code: 'WARN',
      userMessage: 'Be careful',
      severity: 'warning',
      retryable: false,
    });

    toastError({ showError, showWarning }, new Error('boom'));

    expect(showWarning).toHaveBeenCalledWith('Warning', 'Be careful');
    expect(showError).not.toHaveBeenCalled();
  });

  it('wraps mutation handlers and falls back to the generic error toast', () => {
    const showError = vi.fn();
    mockLogError.mockReturnValue({
      code: 'ERR',
      userMessage: 'Something went wrong',
      severity: 'error',
      retryable: false,
    });

    const onError = makeMutationErrorHandler({ showError });
    onError(new Error('boom'));

    expect(showError).toHaveBeenCalledWith('Something went wrong', 'Something went wrong');
  });

  it('returns the user-facing message from the shared error classifier', () => {
    mockHandleError.mockReturnValue({
      code: 'INLINE',
      userMessage: 'Inline message',
      severity: 'error',
      retryable: false,
    });

    expect(getUserMessage('boom')).toBe('Inline message');
  });
});
