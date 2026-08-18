'use client';

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient, type DogfoodLogInput, type KpiSnapshot } from '@/lib/api';
import { queryKeys } from '@/lib/query-keys';
import { DogfoodSection } from '@/features/admin/kpi/KpiDashboard';

function buildWeeklyDogfoodDigest(data: KpiSnapshot) {
  const dogfood = data.system.dogfood;
  const reasonEntries = Object.entries(dogfood.reason_counts);
  const topReason = reasonEntries[0]?.[0] ?? 'None yet';
  const reasonBreakdown =
    reasonEntries.length > 0
      ? ['Reason breakdown:', ...reasonEntries.slice(0, 5).map(([reason, count]) => `- ${reason}: ${count}`)]
      : ['Reason breakdown:', '- None yet'];
  const lines = [
    '# Weekly Dogfood Digest',
    '',
    `Entries this week: ${dogfood.total_entries}`,
    `Unique reasons: ${reasonEntries.length}`,
    `Top reason: ${topReason}`,
    '',
    ...reasonBreakdown,
    '',
    'Recent entries:',
    ...dogfood.recent_entries.map((entry) => {
      const timestamp = new Date(entry.recorded_at).toLocaleString();
      const context = entry.context ? ` | ${entry.context}` : '';
      return `- ${timestamp}: ${entry.external_ai} because ${entry.reason}${context}`;
    }),
  ];

  return lines.join('\n');
}

export default function DogfoodJournalScreen() {
  const queryClient = useQueryClient();
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle');
  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.kpi(7),
    queryFn: () => apiClient.getKpi(7),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  const handleSubmit = async (payload: DogfoodLogInput) => {
    await apiClient.submitDogfoodLog(payload);
    await queryClient.invalidateQueries({ queryKey: queryKeys.kpi(7) });
  };

  const dogfood = data?.system.dogfood;
  const reasonEntries = dogfood ? Object.entries(dogfood.reason_counts) : [];
  const topReason = reasonEntries[0]?.[0] ?? null;
  const uniqueReasons = reasonEntries.length;
  const reasonBreakdown = reasonEntries.slice(0, 3);
  const digest = data ? buildWeeklyDogfoodDigest(data) : '';

  const handleCopyDigest = async () => {
    if (!digest) return;
    try {
      await navigator.clipboard.writeText(digest);
      setCopyState('copied');
      window.setTimeout(() => setCopyState('idle'), 2000);
    } catch {
      setCopyState('failed');
      window.setTimeout(() => setCopyState('idle'), 2000);
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-xl font-semibold">Dogfood Journal</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Log every time Goblin is not enough. The reason list is the product research.
        </p>
      </div>

      {data && (
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => void handleCopyDigest()}
            className="rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium text-text hover:bg-surface-hover"
          >
            {copyState === 'copied'
              ? 'Digest copied'
              : copyState === 'failed'
                ? 'Copy failed'
                : 'Copy weekly digest'}
          </button>
          <span className="text-xs text-muted-foreground">
            Markdown summary for notes, docs, or a status update.
          </span>
        </div>
      )}

      {dogfood && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">Entries this week</div>
            <div data-testid="dogfood-week-entries" className="mt-2 text-2xl font-semibold tabular-nums">
              {dogfood.total_entries}
            </div>
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">Unique reasons</div>
            <div data-testid="dogfood-week-unique-reasons" className="mt-2 text-2xl font-semibold tabular-nums">
              {uniqueReasons}
            </div>
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">Top reason</div>
            <div data-testid="dogfood-week-top-reason" className="mt-2 text-sm font-medium text-foreground">
              {topReason ?? 'None yet'}
            </div>
          </div>
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="text-xs uppercase tracking-wide text-muted-foreground">Reason breakdown</div>
            <div data-testid="dogfood-week-reason-breakdown" className="mt-2 flex flex-col gap-1 text-sm text-foreground">
              {reasonBreakdown.length ? (
                reasonBreakdown.map(([reason, count]) => (
                  <div key={reason} className="flex items-center justify-between gap-3">
                    <span className="min-w-0 flex-1 truncate">{reason}</span>
                    <span className="tabular-nums text-muted-foreground">{count}</span>
                  </div>
                ))
              ) : (
                <span className="text-muted-foreground">None yet</span>
              )}
            </div>
          </div>
        </div>
      )}

      {isLoading && (
        <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
          Loading dogfood log...
        </div>
      )}

      {isError && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          Failed to load dogfood journal:{' '}
          {error instanceof Error ? error.message : 'Unknown error'}
        </div>
      )}

      {data && <DogfoodSection data={data.system.dogfood} onSubmit={handleSubmit} />}
    </div>
  );
}
