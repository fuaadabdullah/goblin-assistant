interface TerminalLine {
  prompt?: string;
  output: string;
}

interface TerminalShowcaseProps {
  lines?: TerminalLine[];
  title?: string;
}

export function TerminalShowcase({
  lines = [
    { prompt: 'goblin@forge', output: ' initialize --env production' },
    { output: '→ Seeding secrets vault… done.' },
    { output: '→ Running diagnostics… all systems go.' },
    { prompt: 'goblin@forge', output: ' deploy goblin-assistant --region iad' },
  ],
  title = 'Goblin Shell',
}: TerminalShowcaseProps) {
  return (
    <section className="space-y-3">
      <div className="flex items-center gap-3">
        <div className="h-3 w-3 rounded-full bg-danger" />
        <div className="h-3 w-3 rounded-full bg-warning" />
        <div className="h-3 w-3 rounded-full bg-success" />
        <span className="text-xs uppercase tracking-[0.2em] text-muted">{title}</span>
      </div>
      <div className="terminal-panel">
        <div className="space-y-2">
          {lines.map((line, idx) => (
            <p key={idx} className="font-mono text-sm leading-relaxed">
              {line.prompt && <span className="prompt mr-2">{line.prompt}$</span>}
              <span className="output">{line.output}</span>
            </p>
          ))}
        </div>
      </div>
    </section>
  );
}
