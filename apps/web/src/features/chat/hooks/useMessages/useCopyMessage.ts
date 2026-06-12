import { useCallback } from 'react';
import { devError, devWarn } from '@/utils/dev-log';
import { useToast } from '../../../../hooks/useToast';
import type { ChatMessage } from '../../types';

interface CopyMessageDeps {
  messages: ChatMessage[];
  showError: ReturnType<typeof useToast>['showError'];
  showSuccess: ReturnType<typeof useToast>['showSuccess'];
}

export const useCopyMessage = ({
  messages,
  showError,
  showSuccess,
}: CopyMessageDeps): ((content: string) => Promise<void>) =>
  useCallback(
    async (content: string) => {
      try {
        await navigator.clipboard.writeText(content);
        devWarn('Message copied to clipboard');
        showSuccess('Copied to clipboard');

        // Fire feedback event for copy (best-effort, fire-and-forget)
        try {
          const { apiClient } = await import('../../../../lib/api');
          const message = messages.find((m) => m.content === content);
          if (message?.id) {
            void apiClient.submitRoutingFeedback({
              requestId: `copy-${message.id}`,
              rating: undefined as any,
              signal: 'copy',
              messageId: message.id,
            });
          }
        } catch {
          // silent - copy feedback is best-effort
        }
      } catch (err) {
        devError('Failed to copy message:', err);
        showError('Copy failed', 'We could not copy that message.');
      }
    },
    [messages, showError, showSuccess]
  );
