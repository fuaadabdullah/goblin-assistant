'use client';

import { useState } from 'react';
import { Copy, RotateCcw, ThumbsDown, ThumbsUp, Trash2 } from 'lucide-react';

interface MessageActionsProps {
  role: 'user' | 'assistant';
  onCopy: () => void;
  onRegenerate?: () => void;
  onDelete?: () => void;
  onThumbsUp?: () => void;
  onThumbsDown?: () => void;
  showRegenerate?: boolean;
  showDelete?: boolean;
}

const MessageActions = ({
  role,
  onCopy,
  onRegenerate,
  onDelete,
  onThumbsUp,
  onThumbsDown,
  showRegenerate = true,
  showDelete = true,
}: MessageActionsProps) => {
  const isAssistantMessage = role === 'assistant';
  const [rated, setRated] = useState<1 | -1 | null>(null);

  const handleThumbsUp = () => {
    if (rated !== null) return;
    setRated(1);
    onThumbsUp?.();
  };

  const handleThumbsDown = () => {
    if (rated !== null) return;
    setRated(-1);
    onThumbsDown?.();
  };

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

      {/* Feedback buttons - assistant messages only, disabled after rating */}
      {isAssistantMessage && (onThumbsUp || onThumbsDown) && (
        <>
          <button
            type="button"
            onClick={handleThumbsUp}
            disabled={rated !== null}
            title="Good response"
            className={`p-1.5 rounded-md transition-colors ${
              rated === 1
                ? 'text-green-500 bg-green-500/10'
                : 'text-muted hover:text-green-500 hover:bg-green-500/10 disabled:opacity-40'
            }`}
            aria-label="Mark response as helpful"
            aria-pressed={rated === 1 ? true : false}
          >
            <ThumbsUp size={16} />
          </button>
          <button
            type="button"
            onClick={handleThumbsDown}
            disabled={rated !== null}
            title="Poor response"
            className={`p-1.5 rounded-md transition-colors ${
              rated === -1
                ? 'text-destructive bg-destructive/10'
                : 'text-muted hover:text-destructive hover:bg-destructive/10 disabled:opacity-40'
            }`}
            aria-label="Mark response as unhelpful"
            aria-pressed={rated === -1 ? true : false}
          >
            <ThumbsDown size={16} />
          </button>
        </>
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
