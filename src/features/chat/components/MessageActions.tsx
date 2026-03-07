'use client';

import { Copy, RotateCcw, Trash2 } from 'lucide-react';

interface MessageActionsProps {
  role: 'user' | 'assistant';
  onCopy: () => void;
  onRegenerate?: () => void;
  onDelete?: () => void;
  showRegenerate?: boolean;
  showDelete?: boolean;
}

const MessageActions = ({
  role,
  onCopy,
  onRegenerate,
  onDelete,
  showRegenerate = true,
  showDelete = true,
}: MessageActionsProps) => {
  const isAssistantMessage = role === 'assistant';

  return (
    <div className="flex items-center gap-1">
      {/* Copy button */}
      <button
        type="button"
        onClick={onCopy}
        title="Copy message"
        className="p-1.5 rounded-md text-muted hover:text-text hover:bg-surface-hover transition-colors"
        aria-label="Copy message content"
      >
        <Copy size={16} />
      </button>

      {/* Regenerate button - assistant messages only */}
      {isAssistantMessage && showRegenerate && onRegenerate && (
        <button
          type="button"
          onClick={onRegenerate}
          title="Regenerate response (resend last message)"
          className="p-1.5 rounded-md text-muted hover:text-text hover:bg-surface-hover transition-colors"
          aria-label="Regenerate response"
        >
          <RotateCcw size={16} />
        </button>
      )}

      {/* Delete button */}
      {showDelete && onDelete && (
        <button
          type="button"
          onClick={onDelete}
          title="Delete message"
          className="p-1.5 rounded-md text-muted hover:text-destructive hover:bg-destructive/10 transition-colors"
          aria-label="Delete message"
        >
          <Trash2 size={16} />
        </button>
      )}
    </div>
  );
};

export default MessageActions;
