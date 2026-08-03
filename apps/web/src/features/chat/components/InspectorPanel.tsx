'use client';

import { X, Cpu, Zap, DollarSign, Layers, GitBranch, Hash, Activity } from 'lucide-react';
import type { ChatMessage } from '../types';
import { formatCost } from '@/utils/format-cost';
import { useUIStore } from '../../../store/uiStore';

interface InspectorPanelProps {
  message: ChatMessage | null;
  isStreaming: boolean;
  sessionTotals: {
    tokens: number;
    costUsd: number;
    messageCount: number;
  };
}

function SectionHeader({ label, icon: Icon }: { label: string; icon?: React.ComponentType<{ className?: string }> }) {
  return (
    <div className="flex items-center gap-1.5 mb-2">
      {Icon && <Icon className="w-3 h-3 text-muted/70" />}
      <span className="text-[10px] font-semibold uppercase tracking-widest text-muted/70">
        {label}
      </span>
    </div>
  );
}

function Field({ label, value, mono = false, dim = false }: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
  dim?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-2 py-1.5 border-b border-border/30 last:border-0">
      <span className="text-xs text-muted flex-shrink-0">{label}</span>
      <span
        className={`text-xs text-right break-all ${
          dim ? 'text-muted/50' : mono ? 'text-text font-mono' : 'text-text'
        }`}
      >
        {value}
      </span>
    </div>
  );
}

function Section({ children }: { children: React.ReactNode }) {
  return <div className="px-4 py-3 border-b border-border/40">{children}</div>;
}

const InspectorPanel = ({ message, isStreaming, sessionTotals }: InspectorPanelProps) => {
  const close = useUIStore((s) => s.setChatInspectorOpen);

  const meta = message?.meta;
  const usage = meta?.usage;
  const inputTok = usage?.input_tokens;
  const outputTok = usage?.output_tokens;
  const totalTok =
    usage?.total_tokens ?? ((inputTok ?? 0) + (outputTok ?? 0) || undefined);
  const cost = typeof meta?.cost_usd === 'number' ? meta.cost_usd : undefined;
  const noMessage = !message;

  return (
    <aside
      className="hidden lg:flex w-80 flex-shrink-0 border-l border-border bg-surface flex-col overflow-y-auto"
      aria-label="Message inspector"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-border/60 flex-shrink-0 sticky top-0 bg-surface z-10">
        <div>
          <h2 className="text-sm font-semibold text-text">Inspector</h2>
          {message && !isStreaming && (
            <p className="text-[10px] text-muted mt-0.5 truncate max-w-[180px]">
              {message.content.slice(0, 60).trim()}
              {message.content.length > 60 ? '…' : ''}
            </p>
          )}
          {isStreaming && (
            <p className="text-[10px] text-primary mt-0.5">Streaming…</p>
          )}
          {noMessage && (
            <p className="text-[10px] text-muted mt-0.5">No message selected</p>
          )}
        </div>
        <button
          type="button"
          onClick={() => close(false)}
          className="p-1.5 rounded-lg text-muted hover:text-text hover:bg-surface-hover transition-colors"
          aria-label="Close inspector"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {noMessage ? (
        <div className="flex-1 flex flex-col items-center justify-center px-6 text-center gap-3">
          <Activity className="w-8 h-8 text-muted/30" />
          <p className="text-xs text-muted">
            Click the inspect button on any assistant message to pin it here.
          </p>
        </div>
      ) : (
        <>
          <Section>
            <SectionHeader label="Model" icon={Cpu} />
            <Field label="Model" value={meta?.model ?? '—'} mono {...(!meta?.model && { dim: true })} />
            <Field label="Provider" value={meta?.provider ?? '—'} mono {...(!meta?.provider && { dim: true })} />
          </Section>

          {(meta?.department || meta?.department_reason) && (
            <Section>
              <SectionHeader label="Routing" icon={GitBranch} />
              {meta.department && <Field label="Brain" value={meta.department} mono />}
              {meta.department_reason && (
                <div className="mt-2">
                  <p className="text-[10px] text-muted uppercase tracking-wide mb-1">Reason</p>
                  <p className="text-xs text-text leading-relaxed">{meta.department_reason}</p>
                </div>
              )}
            </Section>
          )}

          <Section>
            <SectionHeader label="Tokens" icon={Layers} />
            <Field label="Input" value={inputTok !== undefined ? inputTok.toLocaleString() : '—'} mono {...(inputTok === undefined && { dim: true })} />
            <Field label="Output" value={outputTok !== undefined ? outputTok.toLocaleString() : '—'} mono {...(outputTok === undefined && { dim: true })} />
            <Field label="Total" value={totalTok !== undefined ? totalTok.toLocaleString() : '—'} mono {...(totalTok === undefined && { dim: true })} />
          </Section>

          <Section>
            <SectionHeader label="Cost" icon={DollarSign} />
            <Field
              label="This message"
              value={cost !== undefined ? `${formatCost(cost, { mode: 'per-message' })}${meta?.cost_is_approx ? ' ~' : ''}` : '—'}
              mono
              {...(cost === undefined && { dim: true })}
            />
          </Section>

          <Section>
            <SectionHeader label="Latency" icon={Zap} />
            <Field label="Response time" value="—" mono dim />
            <p className="text-[10px] text-muted/50 mt-1">Latency data coming soon.</p>
          </Section>

          <Section>
            <SectionHeader label="Reasoning" />
            {meta?.reasoning_content ? (
              <div>
                {meta.reasoning_tokens !== undefined && (
                  <p className="text-[10px] font-mono text-muted mb-1">
                    {meta.reasoning_tokens.toLocaleString()} reasoning tokens
                  </p>
                )}
                <p className="text-xs text-text leading-relaxed whitespace-pre-wrap font-mono max-h-48 overflow-y-auto">
                  {meta.reasoning_content}
                </p>
              </div>
            ) : (
              <p className="text-xs text-muted/50">No reasoning trace for this message.</p>
            )}
          </Section>

          {meta?.visualizations && meta.visualizations.length > 0 ? (
            <Section>
              <SectionHeader label="Tool Calls" />
              {meta.visualizations.map((viz, i) => (
                <div key={i} className="py-1.5 border-b border-border/30 last:border-0">
                  <p className="text-xs text-text font-mono">{viz.type}</p>
                  <p className="text-[10px] text-muted">{viz.title}</p>
                </div>
              ))}
            </Section>
          ) : (
            <Section>
              <SectionHeader label="Tool Calls" />
              <p className="text-xs text-muted/50">No tool calls in this message.</p>
            </Section>
          )}

          <Section>
            <SectionHeader label="Sources" />
            <p className="text-xs text-muted/50">Citations and web sources will appear here.</p>
          </Section>

          {meta?.correlation_id && (
            <Section>
              <SectionHeader label="Trace" icon={Hash} />
              <Field
                label="Correlation ID"
                value={<span className="font-mono text-[10px] break-all text-muted">{meta.correlation_id}</span>}
              />
            </Section>
          )}
        </>
      )}

      <div className="mt-auto border-t border-border/60 px-4 py-3 flex-shrink-0">
        <SectionHeader label="Session" />
        <div className="grid grid-cols-3 gap-2 mt-1">
          <div className="text-center">
            <p className="text-[11px] font-semibold text-text">{sessionTotals.tokens.toLocaleString()}</p>
            <p className="text-[10px] text-muted">tokens</p>
          </div>
          <div className="text-center border-x border-border/30">
            <p className="text-[11px] font-semibold text-text">{formatCost(sessionTotals.costUsd, { mode: 'per-message' })}</p>
            <p className="text-[10px] text-muted">cost</p>
          </div>
          <div className="text-center">
            <p className="text-[11px] font-semibold text-text">{sessionTotals.messageCount}</p>
            <p className="text-[10px] text-muted">msgs</p>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default InspectorPanel;
