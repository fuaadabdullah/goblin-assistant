import type { ChatMessage, ChatThread, ChatThreadSource } from '../domain/chat';
import { generateMessageId } from './id-generation';
import { devError, devWarn } from '../utils/dev-log';

export const CHAT_THREADS_STORAGE_KEY = 'goblin_chat_threads_v1';
export const CHAT_MESSAGES_STORAGE_PREFIX = 'goblin_chat_messages_v1';
const CHAT_PRELOAD_STORAGE_KEY = 'goblin_preload_chat_v1';

export const sortChatThreads = (threads: ChatThread[]) =>
  [...threads].sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
  );

export const buildThreadKey = (source: ChatThreadSource, conversationId: string) =>
  `${source}:${conversationId}`;

const normalizeStoredThread = (value: unknown): ChatThread | null => {
  if (!value || typeof value !== 'object') return null;

  const raw = value as Partial<ChatThread> & {
    id?: unknown;
    title?: unknown;
    snippet?: unknown;
    createdAt?: unknown;
    updatedAt?: unknown;
    source?: unknown;
    threadKey?: unknown;
  };

  const id = typeof raw.id === 'string' ? raw.id : '';
  if (!id) return null;

  const source: ChatThreadSource =
    raw.source === 'backend' || raw.source === 'legacy-local' ? raw.source : 'legacy-local';
  const nowIso = new Date().toISOString();

  return {
    id,
    source,
    threadKey:
      typeof raw.threadKey === 'string' && raw.threadKey
        ? raw.threadKey
        : buildThreadKey(source, id),
    title: typeof raw.title === 'string' && raw.title ? raw.title : 'Untitled chat',
    snippet: typeof raw.snippet === 'string' ? raw.snippet : '',
    createdAt: typeof raw.createdAt === 'string' && raw.createdAt ? raw.createdAt : nowIso,
    updatedAt: typeof raw.updatedAt === 'string' && raw.updatedAt ? raw.updatedAt : nowIso,
  };
};

export const readChatThreads = (): ChatThread[] => {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(CHAT_THREADS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return sortChatThreads(
      parsed
        .map(item => normalizeStoredThread(item))
        .filter((thread): thread is ChatThread => Boolean(thread))
        .filter(thread => thread.source === 'legacy-local'),
    );
  } catch (error) {
    devWarn('Failed to read chat threads from storage:', error);
    return [];
  }
};

export const writeChatThreads = (threads: ChatThread[]): void => {
  if (typeof window === 'undefined') return;

  const legacyThreads = threads.filter(thread => thread.source === 'legacy-local');
  try {
    window.localStorage.setItem(
      CHAT_THREADS_STORAGE_KEY,
      JSON.stringify(legacyThreads),
    );
  } catch (error) {
    if (error instanceof DOMException && error.name === 'QuotaExceededError') {
      devError('Storage quota exceeded. Attempting to clear old data...');
      // Try to recover by keeping only the most recent threads
      try {
        const recentThreads = legacyThreads.slice(0, 10);
        window.localStorage.setItem(
          CHAT_THREADS_STORAGE_KEY,
          JSON.stringify(recentThreads),
        );
        devWarn('Reduced threads to 10 most recent to fit storage quota');
      } catch (retryError) {
        devError(
          'Failed to persist even after reducing threads:',
          retryError,
        );
      }
    } else {
      devWarn('Failed to persist chat threads:', error);
    }
  }
};

export const removeChatThread = (threadId: string): void => {
  if (typeof window === 'undefined') return;
  const next = readChatThreads().filter(thread => thread.id !== threadId);
  writeChatThreads(next);
};

const messagesKey = (conversationId: string) =>
  `${CHAT_MESSAGES_STORAGE_PREFIX}:${conversationId}`;

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
        : `${generateMessageId()}-${fallbackIndex}`,
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
    devWarn('Failed to read chat messages from storage:', error);
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
      devError(
        'Storage quota exceeded for messages. Attempting to clear old messages...',
      );
      // Try to recover by keeping only the most recent messages
      try {
        const recentMessages = nextMessages.slice(-50); // Keep last 50 messages
        window.localStorage.setItem(
          messagesKey(conversationId),
          JSON.stringify(recentMessages),
        );
        devWarn('Reduced messages to last 50 to fit storage quota');
      } catch (retryError) {
        devError(
          'Failed to persist even after reducing messages:',
          retryError,
        );
      }
    } else {
      devWarn('Failed to persist chat messages:', error);
    }
  }
};

export const removeChatMessages = (conversationId: string): void => {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(messagesKey(conversationId));
  } catch (error) {
    devWarn('Failed to remove chat messages:', error);
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
    devWarn('Failed to store preloaded chat messages:', error);
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
    devWarn('Failed to read preloaded chat messages:', error);
    return null;
  }
};

export const clearPreloadedChat = (): void => {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.removeItem(CHAT_PRELOAD_STORAGE_KEY);
  } catch (error) {
    devWarn('Failed to clear preloaded chat messages:', error);
  }
};
