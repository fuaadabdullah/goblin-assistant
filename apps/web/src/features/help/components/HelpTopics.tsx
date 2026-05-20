interface HelpTopicsProps {
  /** Topics list. */
  topics: { title: string; body: string }[];
}

const HelpTopics = ({ topics }: HelpTopicsProps) => (
  <section className="bg-surface border border-border rounded-2xl p-6">
    <h2 className="text-lg font-semibold text-text mb-4">Common Topics</h2>
    <div className="grid gap-3">
      {topics.map(item => (
        <div key={item.title} className="rounded-xl border border-border bg-surface-hover p-4">
          <h3 className="text-sm font-semibold text-text mb-1">{item.title}</h3>
          <p className="text-xs text-muted">{item.body}</p>
        </div>
      ))}
    </div>
  </section>
);

export default HelpTopics;
