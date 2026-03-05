import type { ChatMessage, ChatThread } from '../domain/chat';

export const CHAT_THREADS_STORAGE_KEY = 'goblin_chat_threads_v1';
export const CHAT_MESSAGES_STORAGE_PREFIX = 'goblin_chat_messages_v1';
const CHAT_PRELOAD_STORAGE_KEY = 'goblin_preload_chat_v1';

export const sortChatThreads = (threads: ChatThread[]) =>
  [...threads].sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
  );

export const readChatThreads = (): ChatThread[] => {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(CHAT_THREADS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return sortChatThreads(parsed.filter(Boolean) as ChatThread[]);
  } catch (error) {
    console.warn('Failed to read chat threads from storage:', error);
    return [];
  }
};

export const writeChatThreads = (threads: ChatThread[]): void => {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(
      CHAT_THREADS_STORAGE_KEY,
      JSON.stringify(threads),
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === 'QuotaExceededError') {
      console.error('Storage quota exceeded. Attempting to clear old data...');
      // Try to recover by keeping only the most recent threads
      try {
        const recentThreads = threads.slice(0, 10);
        window.localStorage.setItem(
          CHAT_THREADS_STORAGE_KEY,
          JSON.stringify(recentThreads),
        );
        console.warn('Reduced threads to 10 most recent to fit storage quota');
      } catch (retryError) {
        console.error(
          'Failed to persist even after reducing threads:',
          retryError,
        );
      }
    } else {
      console.warn('Failed to persist chat threads:', error);
    }
  }
};

const messagesKey = (conversationId: string) =>
  `${CHAT_MESSAGES_STORAGE_PREFIX}:${conversationId}`;

const createLocalId = (): string => {
  if (
    typeof crypto !== 'undefined' &&
    typeof crypto.randomUUID === 'function'
  ) {
    return crypto.randomUUID();
  }
  return `msg-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
};

const normalizeStoredMessage = (
  value: unknown,
  fallbackIndex: number,
): ChatMessage | null => {
  if (!value || typeof value !== 'object') return null;
  const raw = value as Partial<ChatMessage> & {
    role?: unknown;
    content?: unknown;
  };

  const role = typeof raw.role === 'string' ? raw.role : '';
  const content = typeof raw.content === 'string' ? raw.content : '';
  if (!role || !content) return null;

  const nowIso = new Date().toISOString();
  return {
    id:
      typeof raw.id === 'string' && raw.id
        ? raw.id
        : `${createLocalId()}-${fallbackIndex}`,
    createdAt:
      typeof raw.createdAt === 'string' && raw.createdAt
        ? raw.createdAt
        : nowIso,
    role: role as ChatMessage['role'],
    content,
    meta:
      raw.meta && typeof raw.meta === 'object'
        ? (raw.meta as ChatMessage['meta'])
        : undefined,
  };
};

export const readChatMessages = (conversationId: string): ChatMessage[] => {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(messagesKey(conversationId));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((item, idx) => normalizeStoredMessage(item, idx))
      .filter(Boolean) as ChatMessage[];
  } catch (error) {
    console.warn('Failed to read chat messages from storage:', error);
    return [];
  }
};

export const writeChatMessages = (
  conversationId: string,
  nextMessages: ChatMessage[],
): void => {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(
      messagesKey(conversationId),
      JSON.stringify(nextMessages),
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === 'QuotaExceededError') {
      console.error(
        'Storage quota exceeded for messages. Attempting to clear old messages...',
      );
      // Try to recover by keeping only the most recent messages
      try {
        const recentMessages = nextMessages.slice(-50); // Keep last 50 messages
        window.localStorage.setItem(
          messagesKey(conversationId),
          JSON.stringify(recentMessages),
        );
        console.warn('Reduced messages to last 50 to fit storage quota');
      } catch (retryError) {
        console.error(
          'Failed to persist even after reducing messages:',
          retryError,
        );
      }
    } else {
      console.warn('Failed to persist chat messages:', error);
    }
  }
};

export const preloadRecentChat = (
  limit = 5,
): { threadId: string; messages: ChatMessage[] } | null => {
  if (typeof window === 'undefined') return null;
  const threads = readChatThreads();
  if (threads.length === 0) return null;
  const thread = threads[0];
  const messages = readChatMessages(thread.id).slice(-limit);
  const payload = {
    threadId: thread.id,
    messages,
    timestamp: new Date().toISOString(),
  };
  try {
    window.sessionStorage.setItem(
      CHAT_PRELOAD_STORAGE_KEY,
      JSON.stringify(payload),
    );
  } catch (error) {
    console.warn('Failed to store preloaded chat messages:', error);
  }
  return { threadId: thread.id, messages };
};

export const readPreloadedChat = (): {
  threadId: string;
  messages: ChatMessage[];
} | null => {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(CHAT_PRELOAD_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return null;
    if (!Array.isArray(parsed.messages)) return null;
    return {
      threadId: parsed.threadId as string,
      messages: (parsed.messages as unknown[])
        .map((item, idx) => normalizeStoredMessage(item, idx))
        .filter(Boolean) as ChatMessage[],
    };
  } catch (error) {
    console.warn('Failed to read preloaded chat messages:', error);
    return null;
  }
};

export const clearPreloadedChat = (): void => {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.removeItem(CHAT_PRELOAD_STORAGE_KEY);
  } catch (error) {
    console.warn('Failed to clear preloaded chat messages:', error);
  }
};
