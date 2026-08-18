'use client';

import { useState, type FormEvent, type ReactNode } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  apiClient,
  type DogfoodLogInput,
  type KpiModelEval,
  type KpiProviderBreakdown,
  type KpiSnapshot,
} from '@/lib/api';
import { queryKeys } from '@/lib/query-keys';

// ---------------------------------------------------------------------------
// Primitives
// ---------------------------------------------------------------------------

function Stat({
  label,
  value,
  sub,
  warn,
}: {
  label: string;
  value: string | number | null | undefined;
  sub?: string;
  warn?: boolean;
}) {
  const display = value == null ? '—' : String(value);
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-border bg-card p-4">
      <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <span className={`text-2xl font-semibold tabular-nums ${warn ? 'text-destructive' : 'text-foreground'}`}>
        {display}
      </span>
      {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h2>
      {children}
    </section>
  );
}

function Grid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">{children}</div>;
}

function Pill({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
        ok ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
      }`}
    >
      {label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Sub-sections
// ---------------------------------------------------------------------------

function SystemSection({ data }: { data: KpiSnapshot['system'] }) {
  const successWarn = data.success_pct != null && data.success_pct < 95;
  return (
    <Section title="System">
      <Grid>
        <Stat label="Requests" value={data.request_count} />
        <Stat
          label="Success"
          value={data.success_pct != null ? `${data.success_pct}%` : null}
          warn={successWarn}
        />
        <Stat
          label="Request Failures"
          value={data.failure_pct != null ? `${data.failure_pct}%` : null}
          warn={(data.failure_pct ?? 0) > 5}
        />
        <Stat
          label="Provider Failures"
          value={data.provider_failure_pct != null ? `${data.provider_failure_pct}%` : null}
          warn={(data.provider_failure_pct ?? 0) > 5}
        />
        <Stat
          label="Fallbacks"
          value={data.fallback_pct != null ? `${data.fallback_pct}%` : null}
          warn={(data.fallback_pct ?? 0) > 5}
        />
        <Stat
          label="p50 Latency"
          value={data.p50_latency_ms != null ? `${data.p50_latency_ms} ms` : null}
        />
        <Stat
          label="p95 Latency"
          value={data.p95_latency_ms != null ? `${data.p95_latency_ms} ms` : null}
          warn={(data.p95_latency_ms ?? 0) > 5000}
        />
        <Stat label="TTFT" value={data.ttft_ms != null ? `${data.ttft_ms} ms` : null} sub="from chat completions" />
        <Stat label="Tool Success" value={data.tool_success_pct != null ? `${data.tool_success_pct}%` : null} sub="from tool traces" />
        <Stat label="Retrieval Lat." value={data.retrieval_latency_ms != null ? `${data.retrieval_latency_ms} ms` : null} sub="from retrieval traces" />
      </Grid>
    </Section>
  );
}

function EconomicsSection({ data }: { data: KpiSnapshot['economics'] }) {
  const chartData = data.provider_breakdown.slice(0, 8).map((row) => ({
    name: `${row.provider}/${row.model}`.replace('/', '\n'),
    cost: Number(row.cost_usd.toFixed(4)),
    requests: row.requests,
  }));

  return (
    <Section title="Economics">
      <Grid>
        <Stat label="Total Cost" value={data.total_cost_usd != null ? `$${data.total_cost_usd.toFixed(4)}` : null} />
        <Stat
          label="Cost / Request"
          value={data.cost_per_request_usd != null ? `$${data.cost_per_request_usd.toFixed(5)}` : null}
        />
        <Stat
          label="Cost / User / Day"
          value={data.cost_per_user_day_usd != null ? `$${data.cost_per_user_day_usd.toFixed(5)}` : null}
        />
        <Stat
          label="Tokens / Req"
          value={data.tokens_per_request != null ? data.tokens_per_request.toLocaleString() : null}
        />
        <Stat label="Total Tokens" value={data.total_tokens?.toLocaleString()} />
        <Stat label="Routing Savings" value={data.savings_from_routing_usd != null ? `$${data.savings_from_routing_usd.toFixed(4)}` : null} sub="run benchmark to populate" />
      </Grid>

      {chartData.length > 0 && (
        <div className="rounded-lg border border-border bg-card p-4">
          <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Provider Spend Breakdown
          </p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="currentColor" strokeOpacity={0.1} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 10 }}
                interval={0}
                tickFormatter={(v: string) => v.split('/')[0]}
              />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={(v: number) => `$${v}`} />
              <Tooltip
                formatter={(value: unknown) => [`$${value}`, 'Cost']}
                contentStyle={{ fontSize: 12 }}
              />
              <Bar dataKey="cost" radius={[3, 3, 0, 0]}>
                {chartData.map((_, i) => (
                  <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <ProviderTable rows={data.provider_breakdown} />
        </div>
      )}
    </Section>
  );
}

const PALETTE = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe', '#ede9fe', '#f5f3ff', '#faf5ff'];

function ProviderTable({ rows }: { rows: KpiProviderBreakdown[] }) {
  if (!rows.length) return null;
  return (
    <table className="mt-3 w-full text-xs">
      <thead>
        <tr className="border-b border-border text-left text-muted-foreground">
          <th className="pb-1 pr-3 font-medium">Provider</th>
          <th className="pb-1 pr-3 font-medium">Model</th>
          <th className="pb-1 pr-3 text-right font-medium">Reqs</th>
          <th className="pb-1 pr-3 text-right font-medium">Cost</th>
          <th className="pb-1 text-right font-medium">Tokens</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i} className="border-b border-border/50 last:border-0">
            <td className="py-1 pr-3 font-mono">{row.provider}</td>
            <td className="py-1 pr-3 font-mono text-muted-foreground">{row.model}</td>
            <td className="py-1 pr-3 text-right tabular-nums">{row.requests.toLocaleString()}</td>
            <td className="py-1 pr-3 text-right tabular-nums">${row.cost_usd.toFixed(4)}</td>
            <td className="py-1 text-right tabular-nums">{row.tokens.toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ProductSection({ data }: { data: KpiSnapshot['product'] }) {
  return (
    <Section title="Product">
      <Grid>
        <Stat label="Total Users" value={data.total_users} />
        <Stat label="New Users" value={data.new_users_in_window} sub="in window" />
        <Stat label="Returning Users" value={data.returning_users_in_window} sub="in window" />
        <Stat label="Total Convos" value={data.total_conversations} />
        <Stat label="Convos (window)" value={data.conversations_in_window} />
        <Stat
          label="Chats / User"
          value={data.chats_per_user != null ? data.chats_per_user.toFixed(2) : null}
        />
        <Stat label="Avg Session" value={data.avg_session_turns != null ? `${data.avg_session_turns} turns` : null} />
        <Stat label="Memory Facts" value={data.total_memory_facts?.toLocaleString()} />
        <Stat label="Goblins" value={data.goblins_created} sub="from goblin catalog" />
      </Grid>
      {data.feature_usage && <FeatureUsagePanel data={data.feature_usage} />}
      {data.pilot_signals && <PilotSignalsPanel data={data.pilot_signals} />}
    </Section>
  );
}

function FeatureUsagePanel({
  data,
}: {
  data: NonNullable<KpiSnapshot['product']['feature_usage']>;
}) {
  const featureEntries = Object.entries(data.counts).sort((a, b) => b[1] - a[1]);
  const categoryEntries = Object.entries(data.conversation_categories);

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Feature Usage
      </p>
      <div className="flex flex-wrap gap-2">
        {featureEntries.length ? (
          featureEntries.map(([label, count]) => (
            <span
              key={label}
              className="rounded-full border border-border bg-background px-2.5 py-1 text-xs text-foreground"
            >
              {label.replace(/_/g, ' ')}: {count}
            </span>
          ))
        ) : (
          <span className="text-xs text-muted-foreground">No feature usage recorded.</span>
        )}
      </div>
      {categoryEntries.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Conversation Categories
          </p>
          <div className="flex flex-wrap gap-2">
            {categoryEntries.map(([label, count]) => (
              <span
                key={label}
                className="rounded-full border border-border bg-background px-2.5 py-1 text-xs text-foreground"
              >
                {label}: {count}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function PilotSignalsPanel({
  data,
}: {
  data: NonNullable<KpiSnapshot['product']['pilot_signals']>;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Pilot Signals
        </p>
        <span className="text-xs text-muted-foreground">
          {data.total_signals} logged · {data.unique_participants} participants
        </span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {data.top_tags.length ? (
          data.top_tags.map((tag) => (
            <span
              key={tag.tag}
              className="rounded-full border border-border bg-background px-2.5 py-1 text-xs text-foreground"
            >
              {tag.tag}: {tag.count}
            </span>
          ))
        ) : (
          <span className="text-xs text-muted-foreground">No pilot signals yet.</span>
        )}
      </div>
      <div className="mt-4 space-y-2">
        {data.recent_signals.length ? (
          data.recent_signals.slice(0, 4).map((signal) => (
            <div key={signal.ticket_id} className="rounded border border-border/80 bg-background p-3 text-xs">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-foreground">{signal.tag || signal.page || 'Pilot signal'}</span>
                {signal.page && (
                  <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                    {signal.page}
                  </span>
                )}
              </div>
              <p className="mt-1 text-foreground">{signal.note}</p>
              {signal.created_at && (
                <p className="mt-1 text-muted-foreground">
                  {new Date(signal.created_at).toLocaleString()}
                </p>
              )}
            </div>
          ))
        ) : (
          <p className="text-xs text-muted-foreground">No recent pilot notes.</p>
        )}
      </div>
    </div>
  );
}

export function DogfoodSection({
  data,
  onSubmit,
}: {
  data: KpiSnapshot['system']['dogfood'];
  onSubmit: (payload: DogfoodLogInput) => Promise<void>;
}) {
  const [primaryAssistant, setPrimaryAssistant] = useState('Goblin');
  const [externalAi, setExternalAi] = useState('');
  const [reason, setReason] = useState('');
  const [context, setContext] = useState('');
  const [status, setStatus] = useState<'idle' | 'submitting' | 'saved' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  const reasonEntries = Object.entries(data.reason_counts).slice(0, 6);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const payload: DogfoodLogInput = {
      primary_assistant: primaryAssistant.trim() || 'Goblin',
      external_ai: externalAi.trim(),
      reason: reason.trim(),
      context: context.trim() || undefined,
    };
    if (!payload.external_ai || !payload.reason) {
      setError('External AI and reason are required.');
      setStatus('error');
      return;
    }

    setStatus('submitting');
    setError(null);
    try {
      await onSubmit(payload);
      setStatus('saved');
      setExternalAi('');
      setReason('');
      setContext('');
    } catch (err) {
      setStatus('error');
      setError(err instanceof Error ? err.message : 'Failed to save note.');
    }
  };

  return (
    <Section title="Dogfood Log">
      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <form className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4" onSubmit={handleSubmit}>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Primary assistant
              <input
                value={primaryAssistant}
                onChange={(event) => setPrimaryAssistant(event.target.value)}
                className="rounded border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary"
                placeholder="Goblin"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              External AI
              <input
                value={externalAi}
                onChange={(event) => setExternalAi(event.target.value)}
                className="rounded border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary"
                placeholder="Claude"
              />
            </label>
          </div>
          <label className="flex flex-col gap-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Why I switched
            <input
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              className="rounded border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary"
              placeholder="Needed a quicker answer for a deadline"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Context
            <textarea
              value={context}
              onChange={(event) => setContext(event.target.value)}
              className="min-h-24 rounded border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-primary"
              placeholder="Optional context about the fallback"
            />
          </label>
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs text-muted-foreground">
              {status === 'saved'
                ? 'Saved'
                : status === 'submitting'
                  ? 'Saving...'
                  : 'Record every time you reach for another AI.'}
            </span>
            <button
              type="submit"
              className="rounded bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={status === 'submitting'}
            >
              Save Note
            </button>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
        </form>

        <div className="flex flex-col gap-4 rounded-lg border border-border bg-card p-4">
          <div className="grid grid-cols-2 gap-3">
            <Stat label="Entries" value={data.total_entries} />
            <Stat label="Recent" value={data.recent_entries.length} sub="loaded in KPI snapshot" />
          </div>
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Top switch reasons
            </p>
            <div className="flex flex-wrap gap-2">
              {reasonEntries.length ? (
                reasonEntries.map(([label, count]) => (
                  <span
                    key={label}
                    className="rounded-full border border-border bg-background px-2.5 py-1 text-xs text-foreground"
                  >
                    {label}: {count}
                  </span>
                ))
              ) : (
                <span className="text-xs text-muted-foreground">No dogfood notes yet.</span>
              )}
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Recent Entries
            </p>
            <div className="space-y-2">
              {data.recent_entries.length ? (
                data.recent_entries.map((entry) => (
                  <div key={entry.entry_id} className="rounded border border-border/80 bg-background p-3 text-xs">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-foreground">{entry.primary_assistant}</span>
                      <span className="text-muted-foreground">→</span>
                      <span className="font-mono text-foreground">{entry.external_ai}</span>
                      <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                        {entry.source}
                      </span>
                    </div>
                    <p className="mt-1 text-foreground">{entry.reason}</p>
                    {entry.context && <p className="mt-1 text-muted-foreground">{entry.context}</p>}
                    <p className="mt-1 text-muted-foreground">
                      {new Date(entry.recorded_at).toLocaleString()}
                    </p>
                  </div>
                ))
              ) : (
                <p className="text-xs text-muted-foreground">Nothing logged yet.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </Section>
  );
}

function AiSection({ data }: { data: KpiSnapshot['ai'] }) {
  const p = data.providers;
  const intel = data.intelligence_benchmark as Record<string, unknown> | null;
  const mem = data.memory_benchmark as Record<string, unknown> | null;
  const modelEvals = data.provider_model_evals;

  return (
    <Section title="AI">
      <Grid>
        <Stat label="Routing Providers" value={`${p.routing} / ${p.configured}`} sub={`${p.total} total`} />
        <Stat
          label="Open Circuits"
          value={p.open_circuits}
          warn={p.open_circuits > 0}
        />
        <Stat
          label="Router Win Rate"
          value={intel?.router_win_rate != null ? `${(Number(intel.router_win_rate) * 100).toFixed(0)}%` : null}
          sub={intel ? `bench run ${String(intel.run_id ?? '').slice(0, 8)}` : 'run intelligence benchmark'}
        />
        <Stat
          label="Goblin Quality"
          value={intel?.goblin_quality != null ? (intel.goblin_quality as number).toFixed(3) : null}
          sub="vs strongest model"
        />
        <Stat
          label="Memory Score"
          value={mem?.avg_memory_score != null ? (mem.avg_memory_score as number).toFixed(3) : null}
          sub={mem ? `recall ${mem.avg_recall}` : 'run memory benchmark'}
        />
        <Stat
          label="Memory Recall"
          value={mem?.avg_recall != null ? `${(Number(mem.avg_recall) * 100).toFixed(0)}%` : null}
        />
        <Stat
          label="Tool Accuracy"
          value={data.tool_selection_accuracy != null ? `${data.tool_selection_accuracy.toFixed(0)}%` : null}
          sub="from tool traces"
        />
      </Grid>
      {modelEvals.length > 0 && <ProviderEvalTable rows={modelEvals} />}
    </Section>
  );
}

function ProviderEvalTable({ rows }: { rows: KpiModelEval[] }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Eval by Provider / Model
      </p>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border text-left text-muted-foreground">
            <th className="pb-1 pr-3 font-medium">Provider</th>
            <th className="pb-1 pr-3 font-medium">Model</th>
            <th className="pb-1 pr-3 text-right font-medium">Samples</th>
            <th className="pb-1 pr-3 text-right font-medium">Quality</th>
            <th className="pb-1 pr-3 text-right font-medium">Success</th>
            <th className="pb-1 pr-3 text-right font-medium">Fallback</th>
            <th className="pb-1 pr-3 text-right font-medium">TTFT</th>
            <th className="pb-1 text-right font-medium">Cost</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.provider}/${row.model}`} className="border-b border-border/50 last:border-0">
              <td className="py-1 pr-3 font-mono">{row.provider}</td>
              <td className="py-1 pr-3 font-mono text-muted-foreground">{row.model}</td>
              <td className="py-1 pr-3 text-right tabular-nums">{row.sample_count}</td>
              <td className="py-1 pr-3 text-right tabular-nums">
                {row.avg_quality_score != null ? row.avg_quality_score.toFixed(3) : '—'}
              </td>
              <td className="py-1 pr-3 text-right tabular-nums">
                {row.success_rate != null ? `${(row.success_rate * 100).toFixed(0)}%` : '—'}
              </td>
              <td className="py-1 pr-3 text-right tabular-nums">
                {row.fallback_rate != null ? `${(row.fallback_rate * 100).toFixed(0)}%` : '—'}
              </td>
              <td className="py-1 pr-3 text-right tabular-nums">
                {row.avg_ttft_ms != null ? `${row.avg_ttft_ms.toFixed(0)} ms` : '—'}
              </td>
              <td className="py-1 text-right tabular-nums">
                {row.avg_cost_usd != null ? `$${row.avg_cost_usd.toFixed(5)}` : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main dashboard
// ---------------------------------------------------------------------------

export default function KpiDashboard() {
  const [days, setDays] = useState(7);
  const queryClient = useQueryClient();

  const { data, isLoading, isError, error, dataUpdatedAt } = useQuery({
    queryKey: queryKeys.kpi(days),
    queryFn: () => apiClient.getKpi(days),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  const updatedAt = dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : null;

  const handleDogfoodSubmit = async (payload: DogfoodLogInput) => {
    await apiClient.submitDogfoodLog(payload);
    await queryClient.invalidateQueries({ queryKey: queryKeys.kpi(days) });
  };

  return (
    <div className="flex flex-col gap-8 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">KPI Dashboard</h1>
          {updatedAt && (
            <p className="mt-0.5 text-xs text-muted-foreground">Last updated {updatedAt}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Window:</span>
          {[1, 7, 14, 30].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                days === d
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* States */}
      {isLoading && (
        <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
          Loading KPIs…
        </div>
      )}

      {isError && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          Failed to load KPIs:{' '}
          {error instanceof Error ? error.message : 'Unknown error'}
        </div>
      )}

      {data && (
        <>
          <SystemSection data={data.system} />
          <EconomicsSection data={data.economics} />
          <ProductSection data={data.product} />
          <AiSection data={data.ai} />
          <DogfoodSection data={data.system.dogfood} onSubmit={handleDogfoodSubmit} />

          <p className="text-xs text-muted-foreground">
            Generated {new Date(data.generated_at).toLocaleString()} · {data.window_days}d window
            · Cells showing "—" mean no data was available in the selected window; see{' '}
            <code className="font-mono">apps/api/benchmarks/</code> for AI scores.
          </p>
        </>
      )}
    </div>
  );
}
