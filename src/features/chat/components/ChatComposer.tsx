import type { KeyboardEvent, RefObject } from 'react';
import type { QuickPrompt } from '../types';
import Link from 'next/link';
import { CHAT_COMPOSER_PLACEHOLDER, CHAT_COMPOSER_TIP } from '../../../content/brand';

interface ChatComposerProps {
  /** Current input value. */
  input: string;
  /** Input ref for focusing. */
  inputRef: RefObject<HTMLTextAreaElement>;
  /** Whether a message is being sent. */
  isSending: boolean;
  /** Inline prompts shown beneath the composer. */
  quickPrompts: QuickPrompt[];
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

const ChatComposer = ({
  input,
  inputRef,
  isSending,
  quickPrompts,
  onInputChange,
  onClear,
  onSend,
  onKeyDown,
  onPromptClick,
  selectedProvider,
  selectedModel,
  estimatedTokens,
  estimatedCostUsd,
  totalTokens,
  totalCostUsd,
}: ChatComposerProps) => (
  <div className="border-t border-border bg-surface/85 backdrop-blur px-4 py-4">
    <div className="max-w-3xl mx-auto">
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
              Est: <span className="text-text">${(estimatedCostUsd || 0).toFixed(4)}</span> ·{' '}
              <span className="text-text">~{estimatedTokens || 0}</span> tok
            </span>
            <span className="hidden sm:inline-block opacity-70">|</span>
            <span>
              Session: <span className="text-text">{totalTokens || 0}</span> tok ·{' '}
              <span className="text-text">${(totalCostUsd || 0).toFixed(4)}</span>
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
          className="w-full px-3 py-2 bg-transparent focus:outline-none text-text placeholder-muted resize-none min-h-[112px] text-sm md:text-base leading-relaxed"
          disabled={isSending}
          aria-label="Chat message input"
          aria-describedby="chat-composer-meta"
        />
        <div className="flex flex-wrap items-center justify-between gap-3 mt-3">
          <div className="text-xs text-muted">
            Tip: {CHAT_COMPOSER_TIP}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onClear}
              className="px-3 py-2 rounded-lg text-sm font-medium border border-border text-text hover:bg-surface-active"
              type="button"
            >
              Clear
            </button>
            <button
              onClick={onSend}
              disabled={isSending || !input.trim()}
              className="bg-primary hover:brightness-110 disabled:opacity-50 text-text-inverse px-4 py-2 rounded-lg font-medium shadow-glow-primary transition-all"
              type="button"
            >
              {isSending ? 'Sending...' : 'Send'}
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
        Press Enter to send, Shift+Enter for new line
      </p>
    </div>
  </div>
);

export default ChatComposer;
