import type { KeyboardEvent, RefObject } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { chatClient } from '../api';
import { toUiError } from '../../../lib/ui-error';
import type { ChatMessage, ChatThread, QuickPrompt } from '../types';
import { useChatThreads } from './useChatThreads';
import { readChatMessages, writeChatMessages } from '../../../lib/chat-history';
import { CHAT_QUICK_PROMPTS } from '../../../content/brand';
import { estimateFromText, type TextCostEstimate } from '../../../lib/cost-estimate';
import { computeCostUsd } from '../../../lib/llm-rates';
import { useProvider } from '../../../contexts/ProviderContext';

export interface ChatSessionState {
  messages: ChatMessage[];
  input: string;
  isSending: boolean;
  totalTokens: number;
  totalCostUsd: number;
  quickPrompts: QuickPrompt[];
  threads: ChatThread[];
  isThreadsLoading: boolean;
  activeThreadId: string | null;
  inputRef: RefObject<HTMLTextAreaElement>;
  bottomRef: RefObject<HTMLDivElement>;
  selectedProvider?: string;
  selectedModel?: string;
  inputEstimate: TextCostEstimate | null;
  setInput: (value: string) => void;
  sendMessage: (messageOverride?: string) => Promise<void>;
  selectThread: (threadId: string) => void;
  handleClearChat: () => void;
  handlePromptClick: (prompt: string) => void;
  handleKeyDown: (e: KeyboardEvent<HTMLTextAreaElement>) => void;
}

export const useChatSession = (): ChatSessionState => {
  const { threads, isLoading: isThreadsLoading, upsertThread } = useChatThreads();
  const { selectedProvider, selectedModel } = useProvider();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [totalTokens, setTotalTokens] = useState(0);
  const [totalCostUsd, setTotalCostUsd] = useState(0);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const hasHydratedRef = useRef(false);

  const inputEstimate = useMemo(() => {
    const est = estimateFromText(input);
    return est.estimated_tokens > 0 ? est : null;
  }, [input]);

  const quickPrompts = useMemo<QuickPrompt[]>(
    () => CHAT_QUICK_PROMPTS.map(item => ({ label: item.label, prompt: item.prompt })),
    []
  );

  const prefersReducedMotion = useMemo(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false;
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (hasHydratedRef.current) return;
    if (activeThreadId) {
      hasHydratedRef.current = true;
      return;
    }
    if (threads.length > 0) {
      const mostRecent = threads[0];
      setActiveThreadId(mostRecent.id);
      setMessages(readChatMessages(mostRecent.id));
      hasHydratedRef.current = true;
    }
  }, [activeThreadId, threads]);

  const selectThread = useCallback((threadId: string) => {
    setActiveThreadId(threadId);
    setMessages(readChatMessages(threadId));
    setTotalTokens(0);
    setTotalCostUsd(0);
    setInput('');
    hasHydratedRef.current = true;
    inputRef.current?.focus();
  }, []);

  const sendMessage = useCallback(
    async (messageOverride?: string) => {
      const content = (messageOverride ?? input).trim();
      if (!content || isSending) return;

      setIsSending(true);

      const nowIso = new Date().toISOString();
      const mkId = () => {
        if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
          return crypto.randomUUID();
        }
        return `msg-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
      };

      const estimate = estimateFromText(content);
      const userMsg: ChatMessage = {
        id: mkId(),
        createdAt: nowIso,
        role: 'user',
        content,
        meta: {
          estimated_tokens: estimate.estimated_tokens,
          estimated_cost_usd: estimate.estimated_cost_usd,
        },
      };
      const updatedMessages = [...messages, userMsg];
      setMessages(updatedMessages);
      setInput('');

      try {
        let conversationId = activeThreadId;
        let createdAt: string | undefined;

        if (!conversationId) {
          const created = await chatClient.createConversation({
            title: content.slice(0, 48),
          });
          conversationId = created.conversationId;
          createdAt = created.createdAt;
          setActiveThreadId(conversationId);
          upsertThread({
            id: conversationId,
            title: created.title ?? content.slice(0, 48),
            snippet: content,
            createdAt,
          });
        }

        if (!conversationId) {
          throw new Error('Conversation ID unavailable.');
        }

        writeChatMessages(conversationId, updatedMessages);

        // Send structured messages (not a flattened "User:/Assistant:" transcript).
        // Flattened transcripts frequently cause models to roleplay both sides and can balloon latency.
        const messagesForModel = updatedMessages.slice(-20);

        const result = await chatClient.sendMessage({
          conversationId,
          messages: messagesForModel,
          model: selectedModel || undefined,
          provider: selectedProvider || undefined,
        });
        const answer = result?.content || 'No response';
        setMessages(prev => {
          const usage = result?.usage;
          const rawCost = typeof result?.cost_usd === 'number' ? result.cost_usd : undefined;
          const fallbackCost =
            rawCost !== undefined
              ? { cost_usd: rawCost, approx: false, source: 'backend' as const }
              : computeCostUsd(usage, result?.provider, result?.model);
          const assistantMsg: ChatMessage = {
            id: mkId(),
            createdAt: new Date().toISOString(),
            role: 'assistant',
            content: answer,
            meta: {
              provider: result?.provider,
              model: result?.model,
              usage,
              cost_usd: fallbackCost.cost_usd,
              cost_is_approx: fallbackCost.approx,
              correlation_id: result?.correlation_id,
            },
          };
          const next = [...prev, assistantMsg];
          writeChatMessages(conversationId, next);
          return next;
        });
        setTotalTokens(prev => prev + (result?.usage?.total_tokens || 0));
        setTotalCostUsd(prev => {
          const add =
            typeof result?.cost_usd === 'number'
              ? result.cost_usd
              : computeCostUsd(result?.usage, result?.provider, result?.model).cost_usd;
          return Number((prev + (add || 0)).toFixed(6));
        });
        upsertThread({
          id: conversationId,
          snippet: answer,
          updatedAt: new Date().toISOString(),
        });
      } catch (err: unknown) {
        const uiError = toUiError(err, {
          code: 'CHAT_SEND_FAILED',
          userMessage: 'Sorry, we could not send that message right now.',
        });
        const assistantMsg: ChatMessage = {
          id: `msg-error-${Date.now()}`,
          createdAt: new Date().toISOString(),
          role: 'assistant',
          content: uiError.userMessage,
        };
        setMessages(prev => [...prev, assistantMsg]);
      } finally {
        setIsSending(false);
        inputRef.current?.focus();
      }
    },
    [activeThreadId, input, isSending, messages, selectedModel, selectedProvider, upsertThread]
  );

  const handleClearChat = useCallback(() => {
    setMessages([]);
    setTotalTokens(0);
    setTotalCostUsd(0);
    setInput('');
    setActiveThreadId(null);
    hasHydratedRef.current = true;
    inputRef.current?.focus();
  }, []);

  const handlePromptClick = useCallback((prompt: string) => {
    setInput(prompt);
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    },
    [sendMessage]
  );

  return {
    messages,
    input,
    isSending,
    totalTokens,
    totalCostUsd,
    quickPrompts,
    threads,
    isThreadsLoading,
    activeThreadId,
    inputRef,
    bottomRef,
    selectedProvider: selectedProvider || undefined,
    selectedModel: selectedModel || undefined,
    inputEstimate,
    setInput,
    sendMessage,
    selectThread,
    handleClearChat,
    handlePromptClick,
    handleKeyDown,
  };
};
