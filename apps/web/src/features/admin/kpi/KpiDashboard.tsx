'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
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
import { apiClient, type KpiProviderBreakdown, type KpiSnapshot } from '@/lib/api';
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

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h2>
      {children}
    </section>
  );
}

function Grid({ children }: { children: React.ReactNode }) {
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
          label="Failures"
          value={data.failure_pct != null ? `${data.failure_pct}%` : null}
          warn={(data.failure_pct ?? 0) > 5}
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
        <Stat label="TTFT" value={data.ttft_ms != null ? `${data.ttft_ms} ms` : null} sub="not yet instrumented" />
        <Stat label="Tool Success" value={data.tool_success_pct != null ? `${data.tool_success_pct}%` : null} sub="not yet instrumented" />
        <Stat label="Retrieval Lat." value={data.retrieval_latency_ms != null ? `${data.retrieval_latency_ms} ms` : null} sub="not yet instrumented" />
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
        <Stat label="Avg Session" value={data.avg_session_turns != null ? `${data.avg_session_turns} turns` : null} />
        <Stat label="Memory Facts" value={data.total_memory_facts?.toLocaleString()} />
        <Stat label="Goblins" value={data.goblins_created} sub="entity count pending" />
      </Grid>
    </Section>
  );
}

function AiSection({ data }: { data: KpiSnapshot['ai'] }) {
  const p = data.providers;
  const intel = data.intelligence_benchmark as Record<string, unknown> | null;
  const mem = data.memory_benchmark as Record<string, unknown> | null;

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
          label="Mem Recall"
          value={mem?.avg_recall != null ? `${(Number(mem.avg_recall) * 100).toFixed(0)}%` : null}
        />
        <Stat label="Tool Accuracy" value={data.tool_selection_accuracy != null ? `${(data.tool_selection_accuracy * 100).toFixed(0)}%` : null} sub="not yet instrumented" />
      </Grid>
    </Section>
  );
}

// ---------------------------------------------------------------------------
// Main dashboard
// ---------------------------------------------------------------------------

export default function KpiDashboard() {
  const [days, setDays] = useState(7);

  const { data, isLoading, isError, error, dataUpdatedAt } = useQuery({
    queryKey: queryKeys.kpi(days),
    queryFn: () => apiClient.getKpi(days),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  const updatedAt = dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : null;

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

          <p className="text-xs text-muted-foreground">
            Generated {new Date(data.generated_at).toLocaleString()} · {data.window_days}d window
            · Cells showing "—" are not yet instrumented; see{' '}
            <code className="font-mono">apps/api/benchmarks/</code> for AI scores.
          </p>
        </>
      )}
    </div>
  );
}
