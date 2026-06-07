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
  selectedProvider?: string;
  selectedModel?: string;
  pendingAttachments: PendingAttachment[];
  onMessagesLoading?: (loading: boolean) => void;
  onThreadUpdated?: (thread: ChatThread) => void;
  onThreadRemoved?: (thread: ChatThread) => void;
  onThreadsInvalidated?: () => void;
  backendConversationQuery?: {
    isLoading: boolean;
    isFetching: boolean;
    data?: {
      conversationId: string;
      title: string;
      createdAt: string;
      updatedAt: string;
      messages: ChatMessage[];
      pagination?: { has_more?: boolean; offset?: number };
    };
  };
}
