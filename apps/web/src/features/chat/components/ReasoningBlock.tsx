'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, BrainCircuit } from 'lucide-react';

interface ReasoningBlockProps {
  content: string;
  tokenCount?: number;
  isStreaming?: boolean;
}

const ReasoningBlock = ({ content, tokenCount, isStreaming = false }: ReasoningBlockProps) => {
  const [expanded, setExpanded] = useState(false);
  const label = isStreaming ? 'Thinking…' : 'Thought';
  const tokenLabel = tokenCount !== undefined ? `${tokenCount.toLocaleString()} tokens` : undefined;

  return (
    <div className="mb-3 rounded-xl border border-border/50 bg-surface-hover/60 overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-surface-hover transition-colors"
        aria-expanded={expanded}
      >
        <BrainCircuit
          className={`w-3.5 h-3.5 flex-shrink-0 ${isStreaming ? 'text-primary animate-pulse' : 'text-muted'}`}
        />
        <span className="text-xs font-medium text-muted flex-1">{label}</span>
        {tokenLabel && (
          <span className="text-[10px] font-mono text-muted/60 mr-1">{tokenLabel}</span>
        )}
        {isStreaming ? (
          <span className="inline-flex items-center gap-0.5">
            <span className="w-1 h-1 rounded-full bg-primary animate-bounce" />
            <span className="w-1 h-1 rounded-full bg-primary animate-bounce [animation-delay:150ms]" />
            <span className="w-1 h-1 rounded-full bg-primary animate-bounce [animation-delay:300ms]" />
          </span>
        ) : (
          <span className="text-muted/50">
            {expanded ? (
              <ChevronDown className="w-3.5 h-3.5" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5" />
            )}
          </span>
        )}
      </button>
      {expanded && content && (
        <div className="px-3 pb-3 pt-0 border-t border-border/40">
          <p className="text-xs text-muted leading-relaxed whitespace-pre-wrap font-mono mt-2">
            {content}
          </p>
        </div>
      )}
    </div>
  );
};

export default ReasoningBlock;
