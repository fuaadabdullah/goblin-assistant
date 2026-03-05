import type { FormEvent } from 'react';
import { useCallback, useState } from 'react';
import { sendSupportMessage } from '../api';
import { toUiError } from '../../../lib/ui-error';

export interface SupportFormState {
  message: string;
  sent: boolean;
  error: string | null;
  sending: boolean;
  setMessage: (value: string) => void;
  handleSubmit: (e: FormEvent) => Promise<void>;
}

export const useSupportForm = (): SupportFormState => {
  const [message, setMessage] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      if (!message.trim()) return;
      setError(null);
      setSending(true);
      try {
        await sendSupportMessage(message.trim());
        setSent(true);
        setMessage('');
        setTimeout(() => setSent(false), 2500);
      } catch (err) {
        const uiError = toUiError(err, {
          code: 'SUPPORT_MESSAGE_FAILED',
          userMessage: 'We could not send your message. Please try again.',
        });
        setError(uiError.userMessage);
      } finally {
        setSending(false);
      }
    },
    [message]
  );

  return { message, sent, error, sending, setMessage, handleSubmit };
};
