'use client';

import dynamic from 'next/dynamic';
import type { ChatMessage } from '../types';

const MessageMarkdown = dynamic(() => import('./MessageMarkdown'), {
  loading: () => <span className="text-muted text-sm animate-pulse">…</span>,
  ssr: false,
});

interface StreamingMessageProps {
  message: ChatMessage;
  isStreaming: boolean;
  prefersReducedMotion?: boolean;
}

function ThinkingIndicator({ prefersReducedMotion }: { prefersReducedMotion: boolean }) {
  if (prefersReducedMotion) {
    return <span className="text-xs text-muted">Generating…</span>;
  }
  return (
    <div className="flex items-center gap-2 py-1">
      <span className="inline-flex items-center gap-1">
        <span className="w-2 h-2 rounded-full bg-primary/60 animate-bounce" />
        <span className="w-2 h-2 rounded-full bg-primary/60 animate-bounce [animation-delay:150ms]" />
        <span className="w-2 h-2 rounded-full bg-primary/60 animate-bounce [animation-delay:300ms]" />
      </span>
      <span className="text-xs text-muted">Generating…</span>
    </div>
  );
}

const StreamingMessage = ({
  message,
  isStreaming,
  prefersReducedMotion = false,
}: StreamingMessageProps) => {
  const hasContent = message.content.trim().length > 0;

  if (!hasContent && isStreaming) {
    return <ThinkingIndicator prefersReducedMotion={prefersReducedMotion} />;
  }

  return (
    <div className="space-y-1">
      <MessageMarkdown content={message.content} className="text-sm md:text-base leading-relaxed" />
      {isStreaming && !prefersReducedMotion && (
        <span
          className="inline-block w-0.5 h-[1em] bg-text/60 align-middle ml-0.5 animate-pulse"
          aria-hidden="true"
        />
      )}
    </div>
  );
};

export default StreamingMessage;
