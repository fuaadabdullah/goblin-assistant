import type { ChangeEvent, KeyboardEvent, RefObject } from 'react';
import { useEffect, useRef } from 'react';
import type { QuickPrompt } from '../types';
import Link from 'next/link';
import { ArrowUp, Loader2, Paperclip, X } from 'lucide-react';
import { CHAT_COMPOSER_PLACEHOLDER } from '../../../content/brand';
import { AuthRequired } from './AuthRequired';
import { formatCost } from '@/utils/format-cost';
import type { PendingAttachment } from '../hooks/useChatSession';

interface ChatComposerProps {
  input: string;
  inputRef: RefObject<HTMLTextAreaElement | null>;
  isSending: boolean;
  quickPrompts: QuickPrompt[];
  authError?: boolean | undefined;
  onInputChange: (value: string) => void;
  onClear: () => void;
  onSend: () => void;
  onKeyDown: (e: KeyboardEvent<HTMLTextAreaElement>) => void;
  onPromptClick: (prompt: string) => void;
  onFileSelected?: ((files: FileList) => void) | undefined;
  pendingAttachments?: PendingAttachment[] | undefined;
  isUploading?: boolean | undefined;
  onRemoveAttachment?: ((fileId: string) => void) | undefined;
  selectedProvider?: string | undefined;
  selectedModel?: string | undefined;
  estimatedTokens?: number | undefined;
  estimatedCostUsd?: number | undefined;
  totalTokens?: number | undefined;
  totalCostUsd?: number | undefined;
}

const MAX_MESSAGE_LENGTH = 10000;
const MAX_TEXTAREA_HEIGHT = 280;

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
  const canSend = !isSending && !!input.trim() && !isOverLimit;

  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`;
  }, [input, inputRef]);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) onFileSelected?.(files);
    e.target.value = '';
  };

  const modelLabel = selectedModel || selectedProvider || 'auto';

  return (
    <div className="border-t border-border/60 bg-bg/90 backdrop-blur px-4 py-3">
      <div className="max-w-3xl mx-auto space-y-2">
        {authError && <AuthRequired />}

        {quickPrompts.length > 0 && !input && (
          <div className="flex flex-wrap gap-1.5">
            {quickPrompts.slice(0, 3).map((item) => (
              <button
                key={item.label}
                onClick={() => onPromptClick(item.prompt)}
                className="px-3 py-1.5 rounded-full border border-border/60 text-xs text-muted hover:text-text hover:border-border hover:bg-surface-hover transition-colors"
                type="button"
              >
                {item.label}
              </button>
            ))}
          </div>
        )}

        <div
          className={`rounded-2xl border bg-surface shadow-sm transition-shadow focus-within:shadow-md ${
            isOverLimit
              ? 'border-red-400/60 focus-within:border-red-400'
              : 'border-border/60 focus-within:border-primary/40'
          }`}
        >
          {((pendingAttachments && pendingAttachments.length > 0) || isUploading) && (
            <div className="flex flex-wrap items-center gap-2 px-4 pt-3">
              {pendingAttachments?.map((att) => (
                <span
                  key={att.file_id}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-surface-hover text-xs text-text border border-border"
                >
                  <Paperclip className="w-3 h-3 text-muted" />
                  <span className="max-w-[120px] truncate">{att.filename}</span>
                  <button
                    type="button"
                    onClick={() => onRemoveAttachment?.(att.file_id)}
                    className="ml-0.5 text-muted hover:text-text"
                    aria-label={`Remove ${att.filename}`}
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

          <label htmlFor="chat-input" className="sr-only">
            Message
          </label>
          <textarea
            id="chat-input"
            ref={inputRef}
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={CHAT_COMPOSER_PLACEHOLDER}
            rows={1}
            maxLength={MAX_MESSAGE_LENGTH}
            className="w-full px-4 pt-3 pb-1 bg-transparent focus:outline-none text-text placeholder-muted resize-none min-h-[52px] text-sm md:text-base leading-relaxed"
            disabled={isSending}
            aria-label="Chat message input"
          />

          <div className="flex items-center justify-between gap-2 px-3 pb-3">
            <div className="flex items-center gap-1">
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                multiple
                accept=".pdf,.txt,.md,.json,.csv,.xlsx,.doc,.docx,.png,.jpg,.jpeg,.gif"
                onChange={handleFileChange}
                aria-label="Upload file"
              />
              {onFileSelected && (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isSending}
                  className="p-2 rounded-lg text-muted hover:text-text hover:bg-surface-hover disabled:opacity-40 transition-colors"
                  aria-label="Attach file"
                  title="Attach file"
                >
                  <Paperclip className="w-4 h-4" />
                </button>
              )}

              <Link
                href="/settings"
                className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-surface-hover border border-border/60 text-xs text-muted hover:text-text hover:border-border transition-colors"
                title="Change model in settings"
              >
                <span className="font-mono">{modelLabel}</span>
              </Link>

              {(estimatedTokens !== undefined || estimatedCostUsd !== undefined) && (
                <span className="hidden md:inline text-xs text-muted font-mono px-1">
                  ~{estimatedTokens ?? 0} tok · {formatCost(estimatedCostUsd ?? 0, { mode: 'per-message' })}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {totalTokens !== undefined && totalTokens > 0 && (
                <span className="hidden lg:inline text-[10px] text-muted font-mono opacity-60">
                  {totalTokens.toLocaleString()} tok · {formatCost(totalCostUsd ?? 0, { mode: 'per-message' })} session
                </span>
              )}

              {showCounter && (
                <span
                  className={`text-xs font-mono ${
                    isOverLimit ? 'text-red-500 font-semibold' : 'text-muted'
                  }`}
                >
                  {inputLength.toLocaleString()} / {MAX_MESSAGE_LENGTH.toLocaleString()}
                </span>
              )}

              {input && (
                <button
                  type="button"
                  onClick={onClear}
                  className="text-xs text-muted hover:text-text px-2 py-1 rounded-lg hover:bg-surface-hover transition-colors"
                >
                  Clear
                </button>
              )}

              <button
                type="button"
                onClick={onSend}
                disabled={!canSend}
                aria-label={
                  isOverLimit
                    ? `Message exceeds ${MAX_MESSAGE_LENGTH.toLocaleString()} character limit`
                    : 'Send message'
                }
                className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary text-text-inverse disabled:opacity-40 hover:brightness-110 active:scale-95 transition-all shadow-glow-primary"
              >
                {isSending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <ArrowUp className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
        </div>

        <p className="text-[11px] text-muted/60 text-center">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
};

export default ChatComposer;
