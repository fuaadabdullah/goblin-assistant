import { useCallback } from 'react';
import { devError, devWarn } from '@/utils/dev-log';
import { useToast } from '../../../../hooks/useToast';

interface CopyMessageDeps {
  showError: ReturnType<typeof useToast>['showError'];
  showSuccess: ReturnType<typeof useToast>['showSuccess'];
}

export const useCopyMessage = ({
  showError,
  showSuccess,
}: CopyMessageDeps): ((content: string) => Promise<void>) =>
  useCallback(
    async (content: string) => {
      try {
        await navigator.clipboard.writeText(content);
        devWarn('Message copied to clipboard');
        showSuccess('Copied to clipboard');
      } catch (err) {
        devError('Failed to copy message:', err);
        showError('Copy failed', 'We could not copy that message.');
      }
    },
    [showError, showSuccess]
  );
