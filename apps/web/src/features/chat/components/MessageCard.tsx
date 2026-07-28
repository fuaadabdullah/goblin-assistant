'use client';

import { useState, useCallback } from 'react';
import dynamic from 'next/dynamic';
import {
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown,
  RotateCcw,
  Trash2,
  Paperclip,
  Telescope,
} from 'lucide-react';
import type { ChatMessage } from '../types';
import MessageTimestamp from './MessageTimestamp';
import { formatCost } from '@/utils/format-cost';
import { FinancialVisualization } from '@/features/finance';
import type { VisualizationBlock } from '@/features/finance';
import StreamingMessage from './StreamingMessage';
import ReasoningBlock from './ReasoningBlock';

const MessageMarkdown = dynamic(() => import('./MessageMarkdown'), {
  loading: () => <span className="text-muted text-sm animate-pulse">…</span>,
  ssr: false,
});

interface MessageCardProps {
  message: ChatMessage;
  isStreaming?: boolean;
  isInspected?: boolean;
  onCopy?: () => void | Promise<void>;
  onRegenerate?: () => void | Promise<void>;
  onDelete?: () => void;
  onThumbsUp?: () => void;
  onThumbsDown?: () => void;
  onInspect?: () => void;
  prefersReducedMotion?: boolean;
}

function ActionBtn({
  onClick,
  title,
  active,
  children,
}: {
  onClick?: () => void;
  title: string;
  active?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs transition-colors ${
        active
          ? 'text-primary bg-primary/10'
          : 'text-muted hover:text-text hover:bg-surface-hover'
      }`}
    >
      {children}
    </button>
  );
}

const MessageCard = ({
  message,
  isStreaming = false,
  isInspected = false,
  onCopy,
  onRegenerate,
  onDelete,
  onThumbsUp,
  onThumbsDown,
  onInspect,
  prefersReducedMotion = false,
}: MessageCardProps) => {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<1 | -1 | null>(null);

  const isUser = message.role === 'user';

  const handleCopy = useCallback(async () => {
    try {
      await onCopy?.();
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // copy failure is silent
    }
  }, [onCopy]);

  const handleThumbsUp = useCallback(() => {
    setFeedback(1);
    onThumbsUp?.();
  }, [onThumbsUp]);

  const handleThumbsDown = useCallback(() => {
    setFeedback(-1);
    onThumbsDown?.();
  }, [onThumbsDown]);

  if (message.role === 'system') return null;

  if (isUser) {
    return (
      <li className="flex justify-end group/msg">
        <div className="max-w-[80%] flex flex-col items-end gap-1.5">
          <div className="flex items-center gap-2 text-xs text-muted px-1">
            <span className="font-medium">You</span>
            <MessageTimestamp createdAt={message.createdAt} showRelative={false} />
          </div>

          <div className="bg-primary text-text-inverse rounded-2xl rounded-br-sm px-4 py-3 shadow-glow-primary text-sm md:text-base leading-relaxed">
            <MessageMarkdown content={message.content} inverse />
            {message.meta?.attachments && message.meta.attachments.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-white/10">
                {message.meta.attachments.map((att) => (
                  <span
                    key={att.id}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-white/15"
                  >
                    <Paperclip className="w-3 h-3" />
                    <span className="max-w-[120px] truncate">{att.filename}</span>
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-center gap-0.5 opacity-0 group-hover/msg:opacity-100 transition-opacity duration-150 pr-1">
            {onCopy && (
              <ActionBtn onClick={() => void handleCopy()} title="Copy message">
                {copied ? (
                  <Check className="w-3 h-3 text-success" />
                ) : (
                  <Copy className="w-3 h-3" />
                )}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </ActionBtn>
            )}
          </div>
        </div>
      </li>
    );
  }

  // Assistant message — flat, full-width
  const usage = message.meta?.usage;
  const computedTokens = (usage?.input_tokens ?? 0) + (usage?.output_tokens ?? 0);
  const tokens = usage?.total_tokens ?? (computedTokens > 0 ? computedTokens : undefined);
  const cost = typeof message.meta?.cost_usd === 'number' ? message.meta.cost_usd : undefined;
  const model = message.meta?.model;

  return (
    <li
      className={`group/msg rounded-xl -mx-2 px-2 py-1 transition-colors ${
        isInspected ? 'bg-primary/5 ring-1 ring-primary/20' : ''
      }`}
    >
      {/* Header: role label + timestamp + meta pills */}
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <span className="text-xs font-semibold text-text tracking-wide">Goblin</span>
        <MessageTimestamp createdAt={message.createdAt} showRelative={false} />
        {(model || tokens !== undefined || cost !== undefined) && (
          <div className="flex flex-wrap items-center gap-1 ml-auto">
            {model && (
              <span className="px-2 py-0.5 rounded-full bg-surface-hover border border-border/60 text-[10px] font-mono text-muted">
                {model}
              </span>
            )}
            {tokens !== undefined && (
              <span className="px-2 py-0.5 rounded-full bg-surface-hover border border-border/60 text-[10px] font-mono text-muted">
                {tokens.toLocaleString()} tok
              </span>
            )}
            {cost !== undefined && (
              <span className="px-2 py-0.5 rounded-full bg-surface-hover border border-border/60 text-[10px] font-mono text-muted">
                {formatCost(cost, { mode: 'per-message' })}
                {message.meta?.cost_is_approx ? ' ~' : ''}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Reasoning trace (extended thinking) */}
      {(message.meta?.reasoning_content || (isStreaming && !message.content)) && (
        <ReasoningBlock
          content={message.meta?.reasoning_content ?? ''}
          {...(message.meta?.reasoning_tokens !== undefined && { tokenCount: message.meta.reasoning_tokens })}
          isStreaming={isStreaming && !message.content}
        />
      )}

      {/* Content */}
      <div className="text-sm md:text-base leading-relaxed text-text">
        {isStreaming ? (
          <StreamingMessage
            message={message}
            isStreaming={isStreaming}
            prefersReducedMotion={prefersReducedMotion}
          />
        ) : (
          <MessageMarkdown content={message.content} />
        )}

        {message.meta?.visualizations && message.meta.visualizations.length > 0 && (
          <div className="mt-3 space-y-2">
            {message.meta.visualizations.map((viz, idx) => (
              <FinancialVisualization
                key={`viz-${idx}`}
                block={viz as VisualizationBlock}
              />
            ))}
          </div>
        )}

        {message.meta?.attachments && message.meta.attachments.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-border">
            {message.meta.attachments.map((att) => (
              <span
                key={att.id}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-surface-hover text-muted border border-border"
              >
                <Paperclip className="w-3 h-3" />
                <span className="max-w-[120px] truncate">{att.filename}</span>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-0.5 mt-2 opacity-0 group-hover/msg:opacity-100 transition-opacity duration-150">
        {onCopy && (
          <ActionBtn onClick={() => void handleCopy()} title="Copy">
            {copied ? (
              <Check className="w-3 h-3 text-success" />
            ) : (
              <Copy className="w-3 h-3" />
            )}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </ActionBtn>
        )}
        {onThumbsUp && (
          <ActionBtn onClick={handleThumbsUp} title="Helpful" active={feedback === 1}>
            <ThumbsUp className="w-3 h-3" />
          </ActionBtn>
        )}
        {onThumbsDown && (
          <ActionBtn onClick={handleThumbsDown} title="Not helpful" active={feedback === -1}>
            <ThumbsDown className="w-3 h-3" />
          </ActionBtn>
        )}
        {onRegenerate && (
          <ActionBtn onClick={() => void onRegenerate()} title="Regenerate response">
            <RotateCcw className="w-3 h-3" />
            <span className="hidden sm:inline">Regenerate</span>
          </ActionBtn>
        )}
        {onDelete && (
          <ActionBtn onClick={onDelete} title="Delete message">
            <Trash2 className="w-3 h-3" />
          </ActionBtn>
        )}
        {onInspect && (
          <ActionBtn onClick={onInspect} title="Inspect message" active={isInspected}>
            <Telescope className="w-3 h-3" />
          </ActionBtn>
        )}
      </div>
    </li>
  );
};

export default MessageCard;
