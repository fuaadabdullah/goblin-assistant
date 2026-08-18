'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { queryKeys } from '@/lib/query-keys';

const PILOT_ONE_LINER =
  'Goblin gives every AI workload the right model, memory, and tools automatically, instead of locking you into one model.';

const PILOT_INVITE = [
  'Try Goblin for 10 minutes and answer these questions as you go:',
  '- What is a Goblin?',
  '- Why would I make another one?',
  '- Which model am I using?',
  "- Did it remember that?",
  '- Why did that take so long?',
  '- What makes this better than ChatGPT?',
  '',
  'If anything feels confusing, tap the ? button and tell us exactly what happened.',
].join('\n');

const PILOT_PROMPTS = [
  'What is a Goblin?',
  'Why would I make another one?',
  'Which model am I using?',
  'Did it remember that?',
  'Why did that take so long?',
  'What makes this better than ChatGPT?',
];

function buildPilotPacket(
  pilotSignals:
    | {
        total_signals: number;
        unique_participants: number;
        top_tags: Array<{ tag: string; count: number }>;
        recent_signals: Array<{
          ticket_id: string;
          name: string | null;
          email: string | null;
          tag: string | null;
          note: string;
        }>;
      }
    | undefined,
) {
  const rosterLines = pilotSignals?.recent_signals.length
    ? pilotSignals.recent_signals.map((signal) => {
        const person = signal.name || signal.email || 'Anonymous';
        const contact = signal.email || 'no contact';
        const tag = signal.tag || 'uncategorized';
        return `- ${person} (${contact}) — ${tag}: ${signal.note}`;
      })
    : ['- No pilot signals yet.'];

  const tagLines = pilotSignals?.top_tags.length
    ? pilotSignals.top_tags.map((tag) => `- ${tag.tag}: ${tag.count}`)
    : ['- None yet'];

  return [
    '# Goblin pilot packet',
    '',
    `One sentence: ${PILOT_ONE_LINER}`,
    '',
    'Use Goblin first. Ask these questions naturally:',
    ...PILOT_PROMPTS.map((prompt) => `- ${prompt}`),
    '',
    `Participants: ${pilotSignals?.unique_participants ?? 0}`,
    `Signals: ${pilotSignals?.total_signals ?? 0}`,
    '',
    'Top confusion tags:',
    ...tagLines,
    '',
    'Roster:',
    ...rosterLines,
  ].join('\n');
}

export default function PilotKitScreen() {
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle');
  const [packetState, setPacketState] = useState<'idle' | 'copied' | 'failed'>('idle');
  const { data } = useQuery({
    queryKey: queryKeys.kpi(7),
    queryFn: () => apiClient.getKpi(7),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  const pilotSignals = data?.product.pilot_signals;
  const recentSignals = pilotSignals?.recent_signals ?? [];
  const rosterRows = recentSignals.slice(0, 6);
  const pilotPacket = buildPilotPacket(pilotSignals ?? undefined);

  const handleCopyInvite = async () => {
    try {
      await navigator.clipboard.writeText(PILOT_INVITE);
      setCopyState('copied');
      window.setTimeout(() => setCopyState('idle'), 2000);
    } catch {
      setCopyState('failed');
      window.setTimeout(() => setCopyState('idle'), 2000);
    }
  };

  const handleCopyPilotPacket = async () => {
    try {
      await navigator.clipboard.writeText(pilotPacket);
      setPacketState('copied');
      window.setTimeout(() => setPacketState('idle'), 2000);
    } catch {
      setPacketState('failed');
      window.setTimeout(() => setPacketState('idle'), 2000);
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex flex-col gap-2">
        <div className="inline-flex w-fit rounded-full border border-border bg-card px-3 py-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Pilot kit
        </div>
        <h1 className="text-xl font-semibold">5-10 human pilot</h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Give real users almost no instructions. Let them use Goblin first, then record the moments where they
          still reach for something else.
        </p>
      </div>

      <section className="grid gap-3 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            One-sentence answer
          </div>
          <p className="mt-2 text-base font-medium text-foreground">{PILOT_ONE_LINER}</p>
          <p className="mt-3 text-sm text-muted-foreground">
            That is the line to use when someone asks what makes this better than ChatGPT.
          </p>
        </div>

        <div className="rounded-lg border border-border bg-card p-5">
          <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Recruiting target
          </div>
          <div className="mt-2 text-3xl font-semibold tabular-nums text-foreground">5-10</div>
          <p className="mt-3 text-sm text-muted-foreground">
            Five annoyed humans are enough to expose the product friction. No polished onboarding required.
          </p>
        </div>
      </section>

      <section className="rounded-lg border border-border bg-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Copyable invite
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Hand this to someone and watch which question they hit first.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void handleCopyInvite()}
            className="rounded-lg border border-border bg-background px-3 py-2 text-xs font-medium text-text hover:bg-surface-hover"
          >
            {copyState === 'copied'
              ? 'Invite copied'
              : copyState === 'failed'
                ? 'Copy failed'
                : 'Copy invite'}
          </button>
        </div>
        <pre className="mt-4 overflow-x-auto rounded-lg border border-border bg-background p-4 text-sm whitespace-pre-wrap text-foreground">
          {PILOT_INVITE}
        </pre>
      </section>

      <section className="rounded-lg border border-border bg-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Pilot roster
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Track the actual humans using Goblin first and the moments they get confused.
            </p>
          </div>
          <div className="text-xs text-muted-foreground">
            {pilotSignals ? `${pilotSignals.unique_participants} participants` : 'Waiting for KPI snapshot'}
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-background px-4 py-3">
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Shareable packet
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              One copyable brief to hand to a pilot participant or a teammate.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void handleCopyPilotPacket()}
            className="rounded-lg border border-border bg-card px-3 py-2 text-xs font-medium text-text hover:bg-surface-hover"
          >
            {packetState === 'copied'
              ? 'Packet copied'
              : packetState === 'failed'
                ? 'Copy failed'
                : 'Copy pilot packet'}
          </button>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                <th className="pb-2 pr-4 font-medium">Person</th>
                <th className="pb-2 pr-4 font-medium">Signal</th>
                <th className="pb-2 pr-4 font-medium">Last note</th>
              </tr>
            </thead>
            <tbody>
              {rosterRows.length ? (
                rosterRows.map((signal) => (
                  <tr key={signal.ticket_id} className="border-b border-border/60 last:border-0">
                    <td className="py-3 pr-4 align-top">
                      <div className="font-medium text-foreground">
                        {signal.name || signal.email || 'Anonymous'}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {signal.email || signal.page || 'No contact yet'}
                      </div>
                    </td>
                    <td className="py-3 pr-4 align-top">
                      <div className="inline-flex rounded-full border border-border bg-background px-2 py-0.5 text-xs text-foreground">
                        {signal.tag || 'uncategorized'}
                      </div>
                    </td>
                    <td className="py-3 align-top text-sm text-foreground">{signal.note}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="py-3 text-sm text-muted-foreground" colSpan={3}>
                    No pilot signals yet. Share the invite and start the pilot.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border border-border bg-card p-5">
        <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Questions to listen for
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {PILOT_PROMPTS.map((prompt) => (
            <div
              key={prompt}
              className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
            >
              {prompt}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
