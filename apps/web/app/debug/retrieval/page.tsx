'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiClient } from '@/lib/api';
import type { RetrievalHistoryResponse, RetrievalTrace } from '@/lib/api/retrieval-debug';
import styles from './page.module.css';

const formatScore = (score: number) => score.toFixed(3);

function useRetrievalHistory() {
  const [history, setHistory] = useState<RetrievalHistoryResponse | null>(null);
  const [selected, setSelected] = useState<RetrievalTrace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.getRetrievalHistory();
      setHistory(result);
      setSelected((current) => current ?? result.traces[0] ?? null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to load retrieval traces.');
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  return { history, selected, setSelected, loading, error, load };
}

export default function RetrievalDebugger() {
  const state = useRetrievalHistory();
  return (
    <main className={styles['shell']}>
      <DebuggerHeader loading={state.loading} refresh={state.load} />
      {state.error ? (
        <div className={styles['error']} role="alert">
          {state.error}
        </div>
      ) : null}
      <Summary history={state.history} />
      <div className={styles['workspace']}>
        <TraceBrowser
          traces={state.history?.traces ?? []}
          selectedId={state.selected?.request_id ?? null}
          loading={state.loading}
          onSelect={state.setSelected}
        />
        <section className={styles['detail']} aria-live="polite">
          {state.selected ? <TraceDetail trace={state.selected} /> : <EmptySelection />}
        </section>
      </div>
    </main>
  );
}

function DebuggerHeader({ loading, refresh }: { loading: boolean; refresh: () => Promise<void> }) {
  return (
    <header className={styles['header']}>
      <div>
        <p className={styles['eyebrow']}>RAG observability</p>
        <h1>Retrieval debugger</h1>
        <p>Inspect the context selected before an answer reaches the model.</p>
      </div>
      <button
        className={styles['refresh']}
        type="button"
        onClick={() => void refresh()}
        disabled={loading}
      >
        {loading ? 'Loading…' : 'Refresh traces'}
      </button>
    </header>
  );
}

function Summary({ history }: { history: RetrievalHistoryResponse | null }) {
  return (
    <section className={styles['metrics']} aria-label="Retrieval summary">
      <Metric label="Traces" value={history?.summary.total_traces ?? 0} />
      <Metric label="Average latency" value={`${history?.summary.avg_retrieval_time ?? 0} ms`} />
      <Metric label="Average tokens" value={history?.summary.avg_tokens_used ?? 0} />
      <Metric label="Truncations" value={history?.summary.truncation_count ?? 0} warning />
    </section>
  );
}

function TraceBrowser({
  traces,
  selectedId,
  loading,
  onSelect,
}: {
  traces: RetrievalTrace[];
  selectedId: string | null;
  loading: boolean;
  onSelect: (trace: RetrievalTrace) => void;
}) {
  const [filter, setFilter] = useState('');
  const filtered = useMemo(() => filterTraces(traces, filter), [filter, traces]);
  return (
    <aside className={styles['tracePanel']}>
      <label className={styles['searchLabel']}>
        Find a trace
        <input
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          placeholder="Request, model, or user ID"
        />
      </label>
      <div className={styles['traceList']}>
        {filtered.map((trace) => (
          <TraceRow
            key={trace.request_id}
            trace={trace}
            active={selectedId === trace.request_id}
            onSelect={onSelect}
          />
        ))}
        {!loading && filtered.length === 0 ? (
          <p className={styles['empty']}>No matching traces.</p>
        ) : null}
      </div>
    </aside>
  );
}

function filterTraces(traces: RetrievalTrace[], filter: string) {
  const needle = filter.trim().toLowerCase();
  if (!needle) return traces;
  return traces.filter((trace) =>
    [trace.request_id, trace.model_selected, trace.user_id ?? ''].some((value) =>
      value.toLowerCase().includes(needle)
    )
  );
}

function TraceRow({
  trace,
  active,
  onSelect,
}: {
  trace: RetrievalTrace;
  active: boolean;
  onSelect: (trace: RetrievalTrace) => void;
}) {
  return (
    <button
      type="button"
      className={`${styles['traceRow']} ${active ? styles['active'] : ''}`}
      onClick={() => onSelect(trace)}
    >
      <span>{trace.request_id}</span>
      <small>
        {new Date(trace.timestamp).toLocaleString()} · {trace.items_retrieved.length} chunks
      </small>
    </button>
  );
}

function EmptySelection() {
  return <p className={styles['empty']}>Select a trace to inspect its retrieved context.</p>;
}

function Metric({
  label,
  value,
  warning = false,
}: {
  label: string;
  value: string | number;
  warning?: boolean;
}) {
  return (
    <div className={styles['metric']}>
      <span>{label}</span>
      <strong className={warning ? styles['warning'] : ''}>{value}</strong>
    </div>
  );
}

function TraceDetail({ trace }: { trace: RetrievalTrace }) {
  const sortedItems = [...trace.items_retrieved].sort((a, b) => a.rank - b.rank);
  const utilization =
    trace.token_budget > 0 ? Math.round((trace.total_tokens_used / trace.token_budget) * 100) : 0;
  return (
    <>
      <div className={styles['detailHeader']}>
        <div>
          <p className={styles['eyebrow']}>Request</p>
          <h2>{trace.request_id}</h2>
        </div>
        <span className={trace.error ? styles['failedBadge'] : styles['successBadge']}>
          {trace.error ? 'Failed' : 'Complete'}
        </span>
      </div>
      <dl className={styles['facts']}>
        <div>
          <dt>Model</dt>
          <dd>{trace.model_selected}</dd>
        </div>
        <div>
          <dt>Latency</dt>
          <dd>{trace.retrieval_time_ms.toFixed(1)} ms</dd>
        </div>
        <div>
          <dt>Token budget</dt>
          <dd>
            {trace.total_tokens_used} / {trace.token_budget} ({utilization}%)
          </dd>
        </div>
        <div>
          <dt>Context hash</dt>
          <dd title={trace.context_hash}>{trace.context_hash || '—'}</dd>
        </div>
      </dl>
      <div className={styles['chunkHeading']}>
        <h3>Retrieved chunks</h3>
        <span>{sortedItems.length} total</span>
      </div>
      <div className={styles['chunks']}>
        {sortedItems.map((item, index) => (
          <article className={styles['chunk']} key={`${item.source}-${item.source_id ?? index}`}>
            <header>
              <span className={styles['rank']}>#{item.rank}</span>
              <strong>{item.source}</strong>
              <span>score {formatScore(item.relevance_score)}</span>
              <span>{item.token_count} tokens</span>
              {item.truncated ? <span className={styles['truncated']}>truncated</span> : null}
            </header>
            <p>{item.content || 'No content snapshot recorded.'}</p>
            <details>
              <summary>Metadata</summary>
              <pre>{JSON.stringify(item.metadata, null, 2)}</pre>
            </details>
          </article>
        ))}
      </div>
    </>
  );
}
