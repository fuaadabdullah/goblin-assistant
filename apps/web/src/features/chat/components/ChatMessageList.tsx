'use client';

import type { Ref } from 'react';
import { useMemo } from 'react';
import type { ChatMessage, QuickPrompt } from '../types';
import MessageCard from './MessageCard';
import ChatEmptyState from './ChatEmptyState';

interface ChatMessageListProps {
  messages: ChatMessage[];
  quickPrompts: QuickPrompt[];
  onPromptClick: (prompt: string) => void;
  bottomRef: Ref<HTMLDivElement>;
  isSending: boolean;
  isLoading?: boolean;
  onDeleteMessage?: (messageId: string) => void;
  onCopyMessage?: (content: string) => Promise<void>;
  onRegenerateMessage?: (messageId: string) => Promise<void>;
  onRateFeedback?: (messageId: string, rating: 1 | -1) => Promise<void>;
  inspectedMessageId?: string | null;
  onInspectMessage?: (messageId: string) => void;
  prefersReducedMotion?: boolean;
}

const ChatMessageList = ({
  messages,
  quickPrompts,
  onPromptClick,
  bottomRef,
  isSending,
  isLoading = false,
  onDeleteMessage,
  onCopyMessage,
  onRegenerateMessage,
  onRateFeedback,
  inspectedMessageId,
  onInspectMessage,
  prefersReducedMotion = false,
}: ChatMessageListProps) => {
  const messageList = useMemo(() => messages.filter(Boolean), [messages]);

  const streamingMessageId = useMemo(() => {
    if (!isSending) return null;
    const reversed = [...messageList].reverse();
    const lastAssistantIdx = reversed.findIndex((m) => m.role === 'assistant');
    if (lastAssistantIdx === -1) return null;
    return messageList[messageList.length - 1 - lastAssistantIdx]!.id;
  }, [messageList, isSending]);

  if (isLoading) {
    return (
      <section className="max-w-3xl mx-auto space-y-8 py-2" aria-label="Loading conversation">
        {[1, 2].map((n) => (
          <div key={n} className="space-y-2 animate-pulse">
            <div className="h-3 w-24 rounded bg-surface-hover" />
            <div className="h-4 w-full rounded bg-surface-hover" />
            <div className="h-4 w-5/6 rounded bg-surface-hover" />
            <div className="h-4 w-3/4 rounded bg-surface-hover" />
          </div>
        ))}
        <div ref={bottomRef} aria-hidden="true" />
      </section>
    );
  }

  if (messages.length === 0) {
    return (
      <ChatEmptyState
        quickPrompts={quickPrompts}
        onPromptClick={onPromptClick}
        prefersReducedMotion={prefersReducedMotion}
      />
    );
  }

  return (
    <section className="max-w-3xl mx-auto" aria-label="Chat transcript">
      <ol aria-live="polite" aria-relevant="additions" className="space-y-8 py-2">
        {messageList.map((msg) => (
          <MessageCard
            key={msg.id}
            message={msg}
            isStreaming={streamingMessageId === msg.id && isSending}
            isInspected={inspectedMessageId === msg.id}
            prefersReducedMotion={prefersReducedMotion}
            {...(onCopyMessage && { onCopy: () => onCopyMessage(msg.content) })}
            {...(onRegenerateMessage && { onRegenerate: () => onRegenerateMessage(msg.id) })}
            {...(onDeleteMessage && { onDelete: () => onDeleteMessage(msg.id) })}
            {...(onRateFeedback && { onThumbsUp: () => void onRateFeedback(msg.id, 1) })}
            {...(onRateFeedback && { onThumbsDown: () => void onRateFeedback(msg.id, -1) })}
            {...(onInspectMessage && msg.role === 'assistant' && { onInspect: () => onInspectMessage(msg.id) })}
          />
        ))}
      </ol>
      <div ref={bottomRef} aria-hidden="true" />
    </section>
  );
};

export default ChatMessageList;
