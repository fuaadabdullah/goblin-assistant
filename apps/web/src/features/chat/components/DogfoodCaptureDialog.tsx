'use client';

import { useState, type FormEvent } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../../components/ui';
import { apiClient, type DogfoodLogInput } from '@/lib/api';
import { useToast } from '../../../contexts/ToastContext';

const QUICK_REASONS = [
  'Needed deeper web research',
  'Tool execution was annoying',
  "Memory didn't retrieve something",
  'Response was too slow',
  "Coding context wasn't good enough",
  'Wanted file support',
  'Needed image understanding',
  'Model selection sucked',
] as const;

interface DogfoodCaptureDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const INITIAL_FORM: DogfoodLogInput = {
  primary_assistant: 'Goblin',
  external_ai: '',
  reason: '',
  context: '',
};

export default function DogfoodCaptureDialog({
  open,
  onOpenChange,
}: DogfoodCaptureDialogProps) {
  const { showError, showSuccess } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<DogfoodLogInput>(INITIAL_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const setField = <K extends keyof DogfoodLogInput>(key: K, value: DogfoodLogInput[K]) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const resetForm = () => setForm(INITIAL_FORM);

  const handleOpenChange = (nextOpen: boolean) => {
    onOpenChange(nextOpen);
    if (!nextOpen) {
      resetForm();
      setIsSubmitting(false);
    }
  };

  const handleReasonPick = (reason: string) => {
    setField('reason', reason);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const payload: DogfoodLogInput = {
      primary_assistant: form.primary_assistant.trim() || 'Goblin',
      external_ai: form.external_ai.trim(),
      reason: form.reason.trim(),
      context: form.context?.trim() || undefined,
    };

    if (!payload.external_ai || !payload.reason) {
      showError('Dogfood note needs a target and reason', 'Fill in the external AI and why you switched.');
      return;
    }

    setIsSubmitting(true);
    try {
      await apiClient.submitDogfoodLog(payload);
      await queryClient.invalidateQueries({ queryKey: ['admin', 'kpi'] });
      showSuccess('Dogfood note saved', 'Recorded the reason you reached for another assistant.');
      handleOpenChange(false);
    } catch (error) {
      showError(
        'Failed to save dogfood note',
        error instanceof Error ? error.message : 'Could not record the fallback.'
      );
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Log another AI</DialogTitle>
          <DialogDescription>
            Record why Goblin was not enough so the next iteration can attack the real friction.
          </DialogDescription>
        </DialogHeader>

        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="flex flex-col gap-2 text-sm font-medium text-text">
              Primary assistant
              <input
                value={form.primary_assistant}
                onChange={(event) => setField('primary_assistant', event.target.value)}
                className="rounded border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                placeholder="Goblin"
              />
            </label>
            <label className="flex flex-col gap-2 text-sm font-medium text-text">
              External AI
              <input
                value={form.external_ai}
                onChange={(event) => setField('external_ai', event.target.value)}
                className="rounded border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
                placeholder="Claude"
              />
            </label>
          </div>

          <div>
            <div className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Common reasons
            </div>
            <div className="flex flex-wrap gap-2">
              {QUICK_REASONS.map((reason) => (
                <button
                  key={reason}
                  type="button"
                  onClick={() => handleReasonPick(reason)}
                  className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
                    form.reason === reason
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border bg-background text-text hover:bg-surface-hover'
                  }`}
                >
                  {reason}
                </button>
              ))}
            </div>
          </div>

          <label className="flex flex-col gap-2 text-sm font-medium text-text">
            Why did you switch?
            <input
              value={form.reason}
              onChange={(event) => setField('reason', event.target.value)}
              className="rounded border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
              placeholder="Needed deeper web research"
            />
          </label>

          <label className="flex flex-col gap-2 text-sm font-medium text-text">
            Context
            <textarea
              value={form.context ?? ''}
              onChange={(event) => setField('context', event.target.value)}
              className="min-h-28 rounded border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
              placeholder="Optional extra context"
            />
          </label>

          <DialogFooter>
            <button
              type="button"
              onClick={() => handleOpenChange(false)}
              className="rounded border border-border px-4 py-2 text-sm font-medium text-text hover:bg-surface-hover"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Saving…' : 'Save note'}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
