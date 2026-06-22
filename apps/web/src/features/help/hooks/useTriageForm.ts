import type { FormEvent } from 'react';
import { useCallback, useState } from 'react';
import { triageIssue } from '../api';
import type { TriageResponse } from '../api';
import { toUiError } from '../../../lib/ui-error';
import { getUserMessage } from '../../../lib/error/toast';
import { useToast } from '../../../hooks/useToast';

export interface TriageFormState {
  description: string;
  submitting: boolean;
  result: TriageResponse | null;
  error: string | null;
  setDescription: (value: string) => void;
  handleSubmit: (e: FormEvent) => Promise<void>;
  reset: () => void;
}

export const useTriageForm = (): TriageFormState => {
  const { showSuccess, showError } = useToast();
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<TriageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      if (!description.trim()) return;
      setError(null);
      setSubmitting(true);
      try {
        const data = await triageIssue(description.trim());
        setResult(data);
        setDescription('');
        showSuccess('Issue triaged', data.issue_url ? 'GitHub issue created.' : 'Triage complete.');
      } catch (err) {
        const uiError = toUiError(err, {
          code: 'TRIAGE_FAILED',
          userMessage: getUserMessage(err),
        });
        setError(uiError.userMessage);
        showError('Triage failed', uiError.userMessage);
      } finally {
        setSubmitting(false);
      }
    },
    [description, showError, showSuccess]
  );

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setDescription('');
  }, []);

  return { description, submitting, result, error, setDescription, handleSubmit, reset };
};
