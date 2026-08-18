import { Sparkles } from 'lucide-react';

interface SearchQuickQueriesProps {
  /** List of suggested query strings. */
  queries: string[];
  /** Called when a suggestion is selected. */
  onSelect: (value: string) => void;
}

const SearchQuickQueries = ({ queries, onSelect }: SearchQuickQueriesProps) => (
  <div className="bg-surface rounded-xl border border-border p-6 mb-8">
    <div className="flex items-center gap-2 mb-2">
      <Sparkles className="w-4 h-4 text-primary" aria-hidden="true" />
      <h2 className="text-lg font-semibold text-text">Quick Queries</h2>
    </div>
    <p className="text-sm text-muted mb-4">Start with a suggestion or type your own question.</p>
    <div className="flex flex-wrap gap-2">
      {queries.map((value) => (
        <button
          key={value}
          onClick={() => onSelect(value)}
          className="px-3 py-2 rounded-full border border-border text-sm text-text hover:bg-surface-hover hover:border-primary/40 transition-colors"
          type="button"
        >
          {value}
        </button>
      ))}
    </div>
  </div>
);

export default SearchQuickQueries;
