import { useCallback } from 'react';
import type { ChatMessage } from '../../types';
import { useToast } from '../../../../contexts/ToastContext';

interface DeleteMessageDeps {
  messages: ChatMessage[];
  applyMessages: (msgs: ChatMessage[]) => void;
  showSuccess: ReturnType<typeof useToast>['showSuccess'];
}

export const useDeleteMessage = ({
  messages,
  applyMessages,
  showSuccess,
}: DeleteMessageDeps): ((messageId: string) => void) =>
  useCallback(
    (messageId: string) => {
      applyMessages(messages.filter((msg) => msg.id !== messageId));
      showSuccess('Message removed');
    },
    [messages, applyMessages, showSuccess]
  );
