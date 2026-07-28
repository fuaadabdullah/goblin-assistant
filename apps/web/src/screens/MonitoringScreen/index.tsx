'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { useRoutingAudit, useRoutingProviders } from '../../features/admin/providers/hooks/useRoutingAnalytics';
import Seo from '../../components/Seo';

const LogsPage = dynamic(() => import('../LogsPage'), { ssr: false });

type Tab = 'logs' | 'routing' | 'providers';
const TABS: { id: Tab; label: string }[] = [
  { id: 'logs', label: 'Logs' },
  { id: 'routing', label: 'Routing decisions' },
  { id: 'providers', label: 'Provider health' },
];

function pct(n: number) { return `${(n * 100).toFixed(1)}%`; }
function ms(n: number) { return `${Math.round(n)} ms`; }

function RoutingTab() {
  const { data, isLoading } = useRoutingAudit(100);
  const records = data?.records ?? [];
  if (isLoading) return <div className="p-6 text-sm text-muted">Loading routing data…</div>;
  if (records.length === 0) return <div className="p-6 text-sm text-muted">No routing records yet.</div>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border/60">
            {['Time', 'Event', 'Provider', 'Model', 'Latency', 'Cost', 'Tokens'].map((h) => (
              <th key={h} className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-widest text-muted/70 first:pl-0">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {records.map((r, i) => (
            <tr key={`${r.request_id}-${i}`} className="border-b border-border/30 last:border-0 hover:bg-surface-hover/40 transition-colors">
              <td className="px-3 py-2 text-muted font-mono pl-0 whitespace-nowrap">{new Date(r.timestamp * 1000).toLocaleTimeString()}</td>
              <td className="px-3 py-2 text-text">{r.event}</td>
              <td className="px-3 py-2 text-text capitalize">{r.selected_provider ?? r.provider_id ?? '—'}</td>
              <td className="px-3 py-2 text-muted font-mono">{r.model ?? '—'}</td>
              <td className="px-3 py-2 text-text tabular-nums">{r.latency_ms ? `${r.latency_ms} ms` : '—'}</td>
              <td className="px-3 py-2 text-text tabular-nums">{r.cost_usd !== undefined ? `$${r.cost_usd.toFixed(5)}` : '—'}</td>
              <td className="px-3 py-2 text-text tabular-nums">{r.output_tokens !== undefined ? (r.input_tokens ?? 0) + r.output_tokens : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ProvidersTab() {
  const { data, isLoading } = useRoutingProviders();
  const providers = data ? Object.values(data.providers) : [];
  if (isLoading) return <div className="p-6 text-sm text-muted">Loading provider health…</div>;
  if (providers.length === 0) return <div className="p-6 text-sm text-muted">No provider data available.</div>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border/60">
            {['Provider', 'Type', 'EWMA latency', 'p95 latency', 'Success rate', 'Total cost', 'Tokens/sec'].map((h) => (
              <th key={h} className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-widest text-muted/70 first:pl-0">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {providers.map((p) => {
            const rs = p.routing_stats;
            const successColor = rs.success_rate >= 0.99 ? 'text-success' : rs.success_rate >= 0.95 ? 'text-warning' : 'text-error';
            return (
              <tr key={p.id} className="border-b border-border/30 last:border-0 hover:bg-surface-hover/40 transition-colors">
                <td className="px-3 py-2 text-text font-medium capitalize pl-0">{p.name}</td>
                <td className="px-3 py-2 text-muted">{p.type}</td>
                <td className="px-3 py-2 text-text tabular-nums">{ms(rs.ewma_latency_ms)}</td>
                <td className="px-3 py-2 text-text tabular-nums">{ms(rs.p95_latency_ms)}</td>
                <td className={`px-3 py-2 tabular-nums font-semibold ${successColor}`}>{pct(rs.success_rate)}</td>
                <td className="px-3 py-2 text-text tabular-nums">${rs.total_cost_usd.toFixed(4)}</td>
                <td className="px-3 py-2 text-muted tabular-nums">{rs.ewma_tokens_per_sec.toFixed(0)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function MonitoringScreen() {
  const [activeTab, setActiveTab] = useState<Tab>('logs');
  return (
    <div className="min-h-screen bg-bg">
      <Seo title="Monitoring" description="Logs, routing decisions, and provider health" robots="noindex,nofollow" />
      <div className="border-b border-border/60 bg-surface/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4">
          <div className="py-3"><h1 className="text-lg font-semibold text-text">Monitoring</h1></div>
          <div className="flex gap-1 pb-0">
            {TABS.map((t) => (
              <button key={t.id} type="button" onClick={() => setActiveTab(t.id)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === t.id ? 'border-primary text-primary' : 'border-transparent text-muted hover:text-text'}`}>
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-4 py-6">
        {activeTab === 'logs' && <LogsPage />}
        {activeTab === 'routing' && (
          <div className="rounded-xl border border-border bg-surface">
            <div className="px-4 pt-4 pb-1"><p className="text-xs text-muted">Last 100 routing decisions, auto-refreshed every 10s.</p></div>
            <RoutingTab />
          </div>
        )}
        {activeTab === 'providers' && (
          <div className="rounded-xl border border-border bg-surface">
            <div className="px-4 pt-4 pb-1"><p className="text-xs text-muted">Live routing stats, refreshed every 30s.</p></div>
            <ProvidersTab />
          </div>
        )}
      </div>
    </div>
  );
}
