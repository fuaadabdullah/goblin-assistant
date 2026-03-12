'use client';

import type { RefObject } from 'react';
import { useMemo, useState } from 'react';
import type { ChatMessage, QuickPrompt } from '../types';
import StreamingMessage from './StreamingMessage';
import MessageTimestamp from './MessageTimestamp';
import MessageActions from './MessageActions';
import ChatEmptyState from './ChatEmptyState';
import MessageMarkdown from './MessageMarkdown';
import { FinancialVisualization } from '@/features/finance';
import type { VisualizationBlock } from '@/features/finance';
import { Paperclip } from 'lucide-react';
import { formatCost } from '@/utils/format-cost';

interface ChatMessageListProps {
  /** Conversation messages in display order. */
  messages: ChatMessage[];
  /** Suggested prompts displayed when there are no messages. */
  quickPrompts: QuickPrompt[];
  /** Callback for clicking a quick prompt. */
  onPromptClick: (prompt: string) => void;
  /** Scroll anchor for auto-scrolling. */
  bottomRef: RefObject<HTMLDivElement>;
  /** Whether the assistant is currently responding. */
  isSending: boolean;
  /** Whether the selected thread is loading from the backend. */
  isLoading?: boolean;
  /** Handler for deleting a message */
  onDeleteMessage?: (messageId: string) => void;
  /** Handler for copying a message */
  onCopyMessage?: (content: string) => Promise<void>;
  /** Handler for regenerating a response */
  onRegenerateMessage?: (messageId: string) => Promise<void>;
  /** Prefer reduced motion */
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
  prefersReducedMotion = false,
}: ChatMessageListProps) => {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggle = (id: string) => {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const messageList = useMemo(() => messages.filter(Boolean), [messages]);

  // Find the message that is currently streaming
  const streamingMessageId = useMemo(() => {
    if (!isSending) return null;
    // The last assistant message should be streaming if isSending is true
    const lastAssistantIndex = [...messageList]
      .reverse()
      .findIndex((msg) => msg.role === 'assistant');
    if (lastAssistantIndex === -1) return null;
    const assistantMessage = messageList[messageList.length - 1 - lastAssistantIndex];
    return assistantMessage.id;
  }, [messageList, isSending]);

  if (isLoading) {
    return (
      <section className="max-w-4xl mx-auto space-y-4" aria-label="Loading conversation">
        <div className="rounded-2xl border border-border bg-surface/70 p-6 shadow-card animate-pulse">
          <div className="h-4 w-32 rounded bg-surface-hover mb-4" />
          <div className="h-4 w-full rounded bg-surface-hover mb-3" />
          <div className="h-4 w-5/6 rounded bg-surface-hover mb-3" />
          <div className="h-4 w-3/4 rounded bg-surface-hover" />
        </div>
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
    <section className="max-w-4xl mx-auto space-y-6" aria-label="Chat transcript">
      <ol
        aria-live="polite"
        aria-relevant="additions"
        className="space-y-5"
      >
        {messageList.map((msg) => {
          const messageId = msg.id;
          const isUser = msg.role === 'user';
          const detailsId = `msg-details-${messageId}`;
          const isStreaming = streamingMessageId === messageId && isSending;

          const hasMeta =
            !isUser &&
            !!(msg.meta?.model || msg.meta?.provider || msg.meta?.usage || typeof msg.meta?.cost_usd === 'number');
          const isExpanded = !!expanded[messageId];

          const usage = msg.meta?.usage;
          const computedTokens = (usage?.input_tokens || 0) + (usage?.output_tokens || 0);
          const tokens = usage?.total_tokens ?? (computedTokens > 0 ? computedTokens : undefined);
          const cost = typeof msg.meta?.cost_usd === 'number' ? msg.meta.cost_usd : undefined;
          const costLabel = cost !== undefined ? formatCost(cost, { mode: 'per-message' }) : '—';
          const approx = msg.meta?.cost_is_approx ? ' (approx)' : '';

          return (
            <li
              key={messageId}
              className={`flex ${isUser ? 'justify-end' : 'justify-start'} group`}
            >
              <div className={`max-w-[80%] ${isUser ? 'text-right' : 'text-left'}`}>
                {/* Timestamp */}
                <div className="text-xs text-muted mb-1 px-2">
                  <MessageTimestamp createdAt={msg.createdAt} />
                </div>

                {/* Message role label */}
                <div className="text-xs uppercase tracking-wide text-muted mb-1">
                  {isUser ? 'You' : 'Assistant'}
                </div>

                {/* Message bubble container with hover actions */}
                <div className="relative">
                  {/* Message content */}
                  <div
                    className={`rounded-2xl px-4 py-3 leading-relaxed ${
                      isUser
                        ? 'bg-primary text-text-inverse shadow-glow-primary rounded-br-sm'
                        : 'bg-surface text-text border border-border rounded-bl-sm shadow-card'
                    } text-sm md:text-base`}
                  >
                    {isStreaming ? (
                      <StreamingMessage
                        message={msg}
                        isStreaming={isStreaming}
                        prefersReducedMotion={prefersReducedMotion}
                      />
                    ) : (
                      <MessageMarkdown content={msg.content} inverse={isUser} />
                    )}
                    {/* Financial visualizations */}
                    {!isUser && msg.meta?.visualizations && msg.meta.visualizations.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {msg.meta.visualizations.map((viz, idx) => (
                          <FinancialVisualization
                            key={`viz-${idx}`}
                            block={viz as VisualizationBlock}
                          />
                        ))}
                      </div>
                    )}
                    {/* Attachment badges */}
                    {msg.meta?.attachments && msg.meta.attachments.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-current/10">
                        {msg.meta.attachments.map((att) => (
                          <span
                            key={att.id}
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${
                              isUser
                                ? 'bg-white/15 text-text-inverse'
                                : 'bg-surface-hover text-muted border border-border'
                            }`}
                          >
                            <Paperclip className="w-3 h-3" />
                            <span className="max-w-[100px] truncate">{att.filename}</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Message Actions - Hover overlay */}
                  {(onCopyMessage || onDeleteMessage || onRegenerateMessage) && (
                    <div
                      className={`absolute ${
                        isUser ? 'right-0 bottom-0' : 'left-0 bottom-0'
                      } -mb-10 opacity-0 group-hover:opacity-100 transition-opacity duration-200`}
                    >
                      <MessageActions
                        role={msg.role as 'user' | 'assistant'}
                        onCopy={() => onCopyMessage?.(msg.content)}
                        onRegenerate={() =>
                          onRegenerateMessage?.(messageId)
                        }
                        onDelete={() => onDeleteMessage?.(messageId)}
                        showRegenerate={true}
                        showDelete={true}
                      />
                    </div>
                  )}
                </div>

                {/* Metadata Details toggle */}
                {hasMeta ? (
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                    <button
                      type="button"
                      className="px-2 py-1 rounded-md border border-border text-muted hover:text-text hover:bg-surface-hover"
                      onClick={() => toggle(messageId)}
                      aria-controls={detailsId}
                      aria-expanded={isExpanded}
                    >
                      Details
                    </button>
                    <div
                      id={detailsId}
                      className={`${isExpanded ? 'block' : 'hidden'} w-full font-mono text-muted`}
                    >
                      <div className="mt-2 rounded-lg border border-border bg-surface-hover px-3 py-2">
                        <div>
                          model: <span className="text-text">{msg.meta?.model || '—'}</span>
                        </div>
                        <div>
                          provider:{' '}
                          <span className="text-text">{msg.meta?.provider || '—'}</span>
                        </div>
                        <div>
                          tokens: <span className="text-text">{tokens ?? '—'}</span>
                        </div>
                        <div>
                          cost:{' '}
                          <span className="text-text">
                            {costLabel}
                            {approx}
                          </span>
                        </div>
                        {msg.meta?.correlation_id ? (
                          <div className="opacity-80">
                            correlation:{' '}
                            <span className="text-text">{msg.meta.correlation_id}</span>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </div>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>
      <div ref={bottomRef} aria-hidden="true" />
    </section>
  );
};

export default ChatMessageList;
