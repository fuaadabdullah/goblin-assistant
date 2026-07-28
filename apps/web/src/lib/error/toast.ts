import { handleError } from './handler';
import { logError, type ErrorContext } from './logger';

type ShowErrorFn = (title: string, message?: string) => void;
type ShowWarningFn = (title: string, message?: string) => void;

/**
 * Show a toast for any thrown value.
 *
 * Classifies the error, logs it, and calls the appropriate toast helper from
 * `useToast()`.  The caller supplies `showError` / `showWarning` from the hook
 * so this module stays outside the React tree and is testable in isolation.
 *
 * Usage:
 *   const { showError, showWarning } = useToast();
 *   toastError({ showError, showWarning }, error, { action: 'sendMessage' });
 */
export function toastError(
  fns: { showError: ShowErrorFn; showWarning?: ShowWarningFn | undefined },
  error: unknown,
  context: ErrorContext = {}
): void {
  const appError = logError(error, context);

  if (appError.severity === 'warning' && fns.showWarning) {
    fns.showWarning('Warning', appError.userMessage);
  } else {
    fns.showError('Something went wrong', appError.userMessage);
  }
}

/**
 * Convenience wrapper for mutation `onError` callbacks.
 *
 * Usage:
 *   onError: makeMutationErrorHandler({ showError }, { action: 'saveSettings' }),
 */
export function makeMutationErrorHandler(
  fns: { showError: ShowErrorFn; showWarning?: ShowWarningFn | undefined },
  context: ErrorContext = {}
): (error: unknown) => void {
  return (error: unknown) => toastError(fns, error, context);
}

/**
 * Returns the user-facing message for any error without logging or showing a
 * toast — useful for inline error display.
 */
export function getUserMessage(error: unknown): string {
  return handleError(error).userMessage;
}
