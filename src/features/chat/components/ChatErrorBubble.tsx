'use client';

import { AlertTriangle, X } from 'lucide-react';
import type { UiError } from '../../../lib/ui-error';

interface ChatErrorBubbleProps {
  error: UiError;
  onDismiss: () => void;
  onRetry?: () => void;
}

const ChatErrorBubble = ({ error, onDismiss, onRetry }: ChatErrorBubbleProps) => {
  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[80%]">
        <div className="rounded-2xl px-4 py-3 border border-destructive/30 bg-destructive/10 text-destructive shadow-card flex items-start gap-3">
          <AlertTriangle size={18} className="flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium">{error.userMessage}</p>
            {error.code && (
              <p className="text-xs font-mono text-destructive/70 mt-1 opacity-75">
                Error: {error.code}
              </p>
            )}
          </div>
        </div>

        {/* Action buttons */}
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="px-3 py-1.5 rounded-md border border-destructive/30 text-destructive hover:bg-destructive/10 transition-colors"
            >
              Retry
            </button>
          )}
          <button
            type="button"
            onClick={onDismiss}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-muted hover:text-text hover:bg-surface-hover transition-colors"
            aria-label="Dismiss error"
          >
            <X size={14} />
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatErrorBubble;
