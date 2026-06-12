import type { ChatMessage, ChatThread } from '../../types';
import type { PendingAttachment } from '../useChatSession';

export interface MessagesState {
  messages: ChatMessage[];
  isSending: boolean;
  isMessagesLoading: boolean;
  isLoadingOlderMessages: boolean;
  hasMoreMessages: boolean;
  totalTokens: number;
  totalCostUsd: number;
  sendMessage: (messageOverride?: string) => Promise<void>;
  deleteMessage: (messageId: string) => void;
  copyMessage: (content: string) => Promise<void>;
  regenerateMessage: (messageId: string) => Promise<void>;
  loadOlderMessages: () => Promise<void>;
  setMessages: (messages: ChatMessage[]) => void;
}

export interface MessagesProps {
  input: string;
  activeThread: ChatThread | null;
  activeBackendThreadId: string | null;
  selectedProvider?: string | undefined;
  selectedModel?: string | undefined;
  pendingAttachments: PendingAttachment[];
  onMessagesLoading?: ((loading: boolean) => void) | undefined;
  onThreadUpdated?: ((thread: ChatThread) => void) | undefined;
  onThreadRemoved?: ((thread: ChatThread) => void) | undefined;
  onThreadsInvalidated?: (() => void) | undefined;
  backendConversationQuery?:
    | {
        isLoading: boolean;
        isFetching: boolean;
        data?:
          | {
              conversationId: string;
              title: string;
              createdAt: string;
              updatedAt: string;
              messages: ChatMessage[];
              pagination?:
                | { has_more?: boolean | undefined; offset?: number | undefined }
                | undefined;
            }
          | undefined;
      }
    | undefined;
}
