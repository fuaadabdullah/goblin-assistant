import { useState } from 'react';
import { apiClient } from '../lib/api';
import { generateMessageId } from '../lib/id-generation';

interface UseChatStreamingOptions {
  demoMode?: boolean;
  selectedProvider?: string;
  selectedModel?: string;
  onMessageStart?: (messageId: string) => void;
  onMessageUpdate?: (messageId: string, content: string) => void;
  onMessageComplete?: (
    messageId: string,
    metadata: Record<string, unknown>,
  ) => void;
  onError?: (title: string, message?: string) => void;
}

export const useChatStreaming = ({
  demoMode = false,
  selectedProvider,
  selectedModel,
  onMessageStart,
  onMessageUpdate,
  onMessageComplete,
  onError,
}: UseChatStreamingOptions) => {
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (message: string) => {
    const messageId = generateMessageId();
    onMessageStart?.(messageId);
    setIsLoading(true);

    try {
      const response = await apiClient.chatCompletion(
        [{ role: 'user', content: message }],
        selectedModel,
        true,
      );

      // Validate and extract content with proper type checking
      let content: string;
      if (typeof response === 'string') {
        content = response;
      } else if (
        response &&
        typeof response === 'object' &&
        'content' in response
      ) {
        const contentValue = (response as { content: unknown }).content;
        content =
          typeof contentValue === 'string'
            ? contentValue
            : JSON.stringify(response);
      } else {
        content = JSON.stringify(response);
      }

      onMessageUpdate?.(messageId, content);
      onMessageComplete?.(messageId, {
        content,
        provider: selectedProvider,
        model: selectedModel,
        demoMode,
      });
    } catch (error) {
      const messageText =
        error instanceof Error ? error.message : 'Failed to send message';
      onError?.('Chat error', messageText);
    } finally {
      setIsLoading(false);
    }
  };

  return { sendMessage, isLoading };
};
