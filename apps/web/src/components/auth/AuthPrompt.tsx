import Link from 'next/link';
import { useRouter } from 'next/router';
import type { KeyboardEvent } from 'react';
import { useEffect, useId, useRef } from 'react';

interface AuthPromptProps {
  title?: string;
  message?: string;
  mode?: 'modal' | 'inline';
  onClose?: () => void;
  allowGuest?: boolean;
  guestHref?: string;
}

const AuthPrompt = ({
  title = 'Sign in required',
  message = 'Sign in or create an account to continue.',
  mode = 'inline',
  onClose,
  allowGuest = false,
  guestHref = '/sandbox?guest=1',
}: AuthPromptProps) => {
  const router = useRouter();
  const from = typeof router.asPath === 'string' ? router.asPath : '/';
  const loginHref = { pathname: '/login', query: { from } };
  const registerHref = { pathname: '/login', query: { mode: 'register', from } };
  const titleId = useId();
  const messageId = useId();
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  const getFocusableElements = () => {
    const root = dialogRef.current;
    if (!root) return [];
    const nodes = root.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
    );
    return Array.from(nodes);
  };

  useEffect(() => {
    if (mode !== 'modal') return;
    previousFocusRef.current = document.activeElement as HTMLElement | null;
    const frame = requestAnimationFrame(() => {
      const [first] = getFocusableElements();
      first?.focus();
    });
    return () => {
      cancelAnimationFrame(frame);
      previousFocusRef.current?.focus();
    };
  }, [mode]);

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape' && onClose) {
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = getFocusableElements();
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const dialogProps =
    mode === 'modal'
      ? {
          role: 'dialog',
          'aria-modal': true,
          'aria-labelledby': titleId,
          'aria-describedby': messageId,
        }
      : {};

  const content = (
    <div
      ref={dialogRef}
      {...dialogProps}
      onKeyDown={mode === 'modal' ? handleKeyDown : undefined}
      className="bg-surface border border-border rounded-2xl p-6 shadow-xl max-w-md w-full"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 id={titleId} className="text-lg font-semibold text-text">
            {title}
          </h2>
          <p id={messageId} className="text-sm text-muted mt-2">
            {message}
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="text-muted hover:text-text"
            aria-label="Close"
          >
            ✕
          </button>
        )}
      </div>
      <div className="mt-6 flex flex-col gap-2">
        <Link
          href={loginHref}
          className="w-full text-center px-4 py-2 rounded-lg bg-primary text-text-inverse font-medium"
        >
          Sign in
        </Link>
        <Link
          href={registerHref}
          className="w-full text-center px-4 py-2 rounded-lg border border-primary text-primary font-medium"
        >
          Create account
        </Link>
        {allowGuest && (
          <Link
            href={guestHref}
            className="w-full text-center px-4 py-2 rounded-lg bg-surface-hover text-text text-sm"
          >
            Continue as guest
          </Link>
        )}
      </div>
    </div>
  );

  if (mode === 'modal') {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
        {content}
      </div>
    );
  }

  return content;
};

export default AuthPrompt;
