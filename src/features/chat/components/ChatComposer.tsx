import type { ChangeEvent, KeyboardEvent, RefObject } from 'react';
import { useRef } from 'react';
import type { QuickPrompt } from '../types';
import Link from 'next/link';
import { Loader2, Paperclip, X } from 'lucide-react';
import { CHAT_COMPOSER_PLACEHOLDER, CHAT_COMPOSER_TIP } from '../../../content/brand';
import { AuthRequired } from './AuthRequired';
import { formatCost } from '@/utils/format-cost';
import type { PendingAttachment } from '../hooks/useChatSession';

interface ChatComposerProps {
  /** Current input value. */
  input: string;
  /** Input ref for focusing. */
  inputRef: RefObject<HTMLTextAreaElement>;
  /** Whether a message is being sent. */
  isSending: boolean;
  /** Inline prompts shown beneath the composer. */
  quickPrompts: QuickPrompt[];
    /** Whether authentication is required (401/403 error). */
    authError?: boolean;
  /** Update input value. */
  onInputChange: (value: string) => void;
  /** Clear the current chat. */
  onClear: () => void;
  /** Send the message. */
  onSend: () => void;
  /** Keyboard handler for Enter/Shift+Enter. */
  onKeyDown: (e: KeyboardEvent<HTMLTextAreaElement>) => void;
  /** Handler for quick prompt selection. */
  onPromptClick: (prompt: string) => void;
  /** Handler for file selection (optional until backend supports uploads). */
  onFileSelected?: (files: FileList) => void;
  /** Pending file attachments to display as chips. */
  pendingAttachments?: PendingAttachment[];
  /** Whether a file upload is in progress. */
  isUploading?: boolean;
  /** Remove a pending attachment. */
  onRemoveAttachment?: (fileId: string) => void;

  /** Selected provider/model for visibility (may be auto). */
  selectedProvider?: string;
  selectedModel?: string;
  /** Live estimate for the current input. */
  estimatedTokens?: number;
  estimatedCostUsd?: number;
  /** Session totals (actual or approximate). */
  totalTokens?: number;
  totalCostUsd?: number;
}

const MAX_MESSAGE_LENGTH = 10000;

const ChatComposer = ({
  input,
  inputRef,
  isSending,
  quickPrompts,
    authError,
  onInputChange,
  onClear,
  onSend,
  onKeyDown,
  onPromptClick,
  onFileSelected,
  pendingAttachments,
  isUploading,
  onRemoveAttachment,
  selectedProvider,
  selectedModel,
  estimatedTokens,
  estimatedCostUsd,
  totalTokens,
  totalCostUsd,
}: ChatComposerProps) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const inputLength = input.length;
  const isOverLimit = inputLength > MAX_MESSAGE_LENGTH;
  const showCounter = inputLength > 9000;

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFileSelected?.(files);
    }
    // Reset so the same file can be re-selected
    e.target.value = '';
  };

  return (
  <div className="border-t border-border bg-surface/85 backdrop-blur px-4 py-4">
    <div className="max-w-3xl mx-auto">
            {authError && (
              <div className="mb-4">
                <AuthRequired />
              </div>
            )}
      <div className="bg-surface-hover border border-border rounded-2xl p-4 focus-within:ring-1 focus-within:ring-primary/40 focus-within:border-primary/40 transition">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3 text-xs text-muted">
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-mono">
              Provider: <span className="text-text">{selectedProvider || 'auto'}</span>
            </span>
            <span className="font-mono">
              Model: <span className="text-text">{selectedModel || 'auto'}</span>
            </span>
            <Link href="/settings" className="text-primary hover:underline">
              Settings
            </Link>
          </div>
          <div className="flex flex-wrap items-center gap-3 font-mono" id="chat-composer-meta">
            <span>
              Est: <span className="text-text">{formatCost(estimatedCostUsd || 0, { mode: 'per-message' })}</span> ·{' '}
              <span className="text-text">~{estimatedTokens || 0}</span> tok
            </span>
            <span className="hidden sm:inline-block opacity-70">|</span>
            <span>
              Session: <span className="text-text">{totalTokens || 0}</span> tok ·{' '}
              <span className="text-text">{formatCost(totalCostUsd || 0, { mode: 'per-message' })}</span>
            </span>
          </div>
        </div>
        <label htmlFor="chat-input" className="sr-only">
          Message
        </label>
        <textarea
          id="chat-input"
          ref={inputRef}
          value={input}
          onChange={e => onInputChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={CHAT_COMPOSER_PLACEHOLDER}
          rows={3}
          maxLength={MAX_MESSAGE_LENGTH}
          className="w-full px-3 py-2 bg-transparent focus:outline-none text-text placeholder-muted resize-none min-h-[112px] text-sm md:text-base leading-relaxed"
          disabled={isSending}
          aria-label="Chat message input"
          aria-describedby="chat-composer-meta"
        />
        {/* Pending attachment chips */}
        {((pendingAttachments && pendingAttachments.length > 0) || isUploading) && (
          <div className="flex flex-wrap items-center gap-2 px-3 pt-2">
            {pendingAttachments?.map((attachment) => (
              <span
                key={attachment.file_id}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-surface-active text-xs text-text border border-border"
              >
                <Paperclip className="w-3 h-3 text-muted" />
                <span className="max-w-[120px] truncate">{attachment.filename}</span>
                <button
                  type="button"
                  onClick={() => onRemoveAttachment?.(attachment.file_id)}
                  className="ml-0.5 text-muted hover:text-text"
                  aria-label={`Remove ${attachment.filename}`}
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
            {isUploading && (
              <span className="inline-flex items-center gap-1 px-2 py-1 text-xs text-muted">
                <Loader2 className="w-3 h-3 animate-spin" />
                Uploading…
              </span>
            )}
          </div>
        )}
        <div className="flex flex-wrap items-center justify-between gap-3 mt-3">
          <div className="flex items-center gap-3">
            <div className="text-xs text-muted">
              Tip: {CHAT_COMPOSER_TIP}
            </div>
            {showCounter && (
              <div className={`text-xs font-mono ${
                isOverLimit ? 'text-red-500 font-semibold' : 'text-muted'
              }`}>
                {inputLength.toLocaleString()} / {MAX_MESSAGE_LENGTH.toLocaleString()}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              multiple
              accept=".pdf,.txt,.md,.json,.csv,.xlsx,.doc,.docx,.png,.jpg,.jpeg,.gif"
              onChange={handleFileChange}
              aria-label="Upload file"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isSending}
              className="px-3 py-2 rounded-lg text-sm font-medium border border-border text-text hover:bg-surface-active disabled:opacity-50"
              type="button"
              aria-label="Attach file"
              title="Attach file"
            >
              <Paperclip className="w-4 h-4" />
            </button>
            <button
              onClick={onClear}
              className="px-3 py-2 rounded-lg text-sm font-medium border border-border text-text hover:bg-surface-active"
              type="button"
            >
              Clear
            </button>
            <button
              onClick={onSend}
              disabled={isSending || !input.trim() || isOverLimit}
              className="bg-primary hover:brightness-110 disabled:opacity-50 text-text-inverse px-4 py-2 rounded-lg font-medium shadow-glow-primary transition-all"
              type="button"
              aria-label={isOverLimit ? `Message exceeds ${MAX_MESSAGE_LENGTH} character limit` : 'Send message'}
            >
              {isSending ? <><Loader2 className="w-4 h-4 animate-spin inline-block mr-1" />Sending…</> : 'Send'}
            </button>
          </div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {quickPrompts.slice(0, 3).map(item => (
          <button
            key={`inline-${item.label}`}
            onClick={() => onPromptClick(item.prompt)}
            className="px-3 py-2 rounded-full border border-border text-xs text-text hover:bg-surface-hover"
            type="button"
          >
            {item.label}
          </button>
        ))}
      </div>

      <p className="text-xs text-muted text-center mt-2">
        Press Enter or Ctrl+Enter to send, Shift+Enter for new line
      </p>
    </div>
  </div>
  );
};

export default ChatComposer;
