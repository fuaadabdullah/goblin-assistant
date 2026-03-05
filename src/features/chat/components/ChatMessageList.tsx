import type { RefObject } from 'react';
import { useMemo, useState } from 'react';
import type { ChatMessage, QuickPrompt } from '../types';

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
}

const ChatMessageList = ({
  messages,
  quickPrompts,
  onPromptClick,
  bottomRef,
  isSending,
}: ChatMessageListProps) => {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggle = (id: string) => {
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const messageList = useMemo(() => messages.filter(Boolean), [messages]);

  if (messages.length === 0) {
    return (
      <section className="flex flex-col items-center justify-center h-full text-center">
        <div className="mb-6 rounded-2xl border border-border bg-surface/70 p-8 shadow-card max-w-xl">
          <div className="w-16 h-16 bg-primary/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl">🤖</span>
          </div>
          <h2 className="text-2xl font-semibold text-text mb-2">
            Welcome! What do you need help with?
          </h2>
          <p className="text-muted">
            Type a question or choose a suggestion to get started.
          </p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            {quickPrompts.map(item => (
              <button
                key={item.label}
                onClick={() => onPromptClick(item.prompt)}
                className="px-3 py-2 rounded-full border border-border text-sm text-text hover:bg-surface-hover"
                type="button"
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        <div ref={bottomRef} aria-hidden="true" />
      </section>
    );
  }

  return (
    <section className="max-w-4xl mx-auto space-y-6" aria-label="Chat transcript">
      <ol
        aria-live="polite"
        aria-relevant="additions"
        className="space-y-5"
      >
        {messageList.map((msg, idx) => {
          const messageId = msg.id || `msg-${idx}`;
          const isUser = msg.role === 'user';
          const detailsId = `msg-details-${messageId}`;
          const hasMeta =
            !isUser &&
            !!(msg.meta?.model || msg.meta?.provider || msg.meta?.usage || typeof msg.meta?.cost_usd === 'number');
          const isExpanded = !!expanded[messageId];

          const usage = msg.meta?.usage;
          const computedTokens = (usage?.input_tokens || 0) + (usage?.output_tokens || 0);
          const tokens = usage?.total_tokens ?? (computedTokens > 0 ? computedTokens : undefined);
          const cost = typeof msg.meta?.cost_usd === 'number' ? msg.meta.cost_usd : undefined;
          const costLabel = cost !== undefined ? `$${cost.toFixed(4)}` : '—';
          const approx = msg.meta?.cost_is_approx ? ' (approx)' : '';
          return (
            <li key={idx} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] ${isUser ? 'text-right' : 'text-left'}`}>
                <div className="text-xs uppercase tracking-wide text-muted mb-1">
                  {isUser ? 'You' : 'Assistant'}
                </div>
                <div
                  className={`rounded-2xl px-4 py-3 leading-relaxed ${
                    isUser
                      ? 'bg-primary text-text-inverse shadow-glow-primary rounded-br-sm'
                      : 'bg-surface text-text border border-border rounded-bl-sm shadow-card'
                  } whitespace-pre-wrap text-sm md:text-base`}
                >
                  {msg.content}
                </div>
                {hasMeta ? (
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                    <button
                      type="button"
                      className="px-2 py-1 rounded-md border border-border text-muted hover:text-text hover:bg-surface-hover"
                      onClick={() => toggle(messageId)}
                      aria-controls={detailsId}
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
                          provider: <span className="text-text">{msg.meta?.provider || '—'}</span>
                        </div>
                        <div>
                          tokens: <span className="text-text">{tokens ?? '—'}</span>
                        </div>
                        <div>
                          cost: <span className="text-text">{costLabel}{approx}</span>
                        </div>
                        {msg.meta?.correlation_id ? (
                          <div className="opacity-80">
                            correlation: <span className="text-text">{msg.meta.correlation_id}</span>
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
