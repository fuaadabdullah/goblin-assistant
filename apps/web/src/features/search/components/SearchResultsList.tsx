import type { ReactNode } from 'react';
import { FileText, MessageSquare, Code, Archive, Brain, Search } from 'lucide-react';
import type { SearchResult } from '../types';

interface SearchResultsListProps {
  /** Search results to render. */
  results: SearchResult[];
  /** Query used to highlight matching result terms. */
  query?: string;
}

/** Map source type to a friendly label, icon, and color class. */
function getSourceMeta(sourceType?: string) {
  switch (sourceType?.toLowerCase()) {
    case 'file':
    case 'document':
      return { icon: FileText, label: 'Document', color: 'bg-info/20 text-info' };
    case 'chat':
    case 'conversation':
    case 'message':
      return { icon: MessageSquare, label: 'Message', color: 'bg-accent/20 text-accent' };
    case 'snippet':
    case 'code':
      return { icon: Code, label: 'Code', color: 'bg-success/20 text-success' };
    case 'archive':
      return { icon: Archive, label: 'Archive', color: 'bg-warning/20 text-warning' };
    case 'task':
      return { icon: Archive, label: 'Task', color: 'bg-warning/20 text-warning' };
    case 'memory':
      return { icon: Brain, label: 'Memory', color: 'bg-primary/20 text-primary' };
    default:
      return { icon: Search, label: 'Result', color: 'bg-surface-hover text-muted' };
  }
}

/** Human-readable relevance label and color from score. */
function relevanceMeta(score: number): { label: string; color: string } {
  if (score >= 0.75) {
    return { label: 'High relevance', color: 'bg-success/20 text-success' };
  }
  if (score >= 0.5) {
    return { label: 'Good match', color: 'bg-info/20 text-info' };
  }
  if (score >= 0.25) {
    return { label: 'Partial match', color: 'bg-warning/20 text-warning' };
  }
  return { label: 'Low relevance', color: 'bg-surface-hover text-muted' };
}

function getSearchTerms(query: string): Array<{ raw: string; escaped: string }> {
  const seen = new Set<string>();
  return query
    .trim()
    .split(/\s+/)
    .map((term) => ({ raw: term, escaped: term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') }))
    .filter((term) => {
      const normalized = term.raw.toLowerCase();
      if (!normalized || seen.has(normalized)) return false;
      seen.add(normalized);
      return true;
    });
}

/** Highlight matching query terms without injecting HTML. */
function highlightMatches(text: string, query = ''): ReactNode[] | string {
  const terms = getSearchTerms(query);
  if (terms.length === 0) return text;

  const matcher = new RegExp(`(${terms.map((term) => term.escaped).join('|')})`, 'gi');
  return text.split(matcher).map((part, index) => {
    if (!terms.some((term) => part.toLowerCase() === term.raw.toLowerCase())) {
      return part;
    }

    return (
      <mark key={`${part}-${index}`} className="rounded-sm bg-primary/30 px-0.5 text-text">
        {part}
      </mark>
    );
  });
}

const SearchResultsList = ({ results, query = '' }: SearchResultsListProps) => (
  <div className="space-y-4">
    <h2 className="text-xl font-semibold text-text mb-4">Search Results ({results.length})</h2>
    {results.map((result, index) => {
      const meta = getSourceMeta(
        (result.metadata?.['source_type'] as string) ||
          (result.metadata?.['sourceType'] as string) ||
          undefined
      );
      const Icon = meta.icon;
      const score =
        result.score ?? (result.distance !== undefined ? 1 - result.distance : undefined);
      const relevance = score !== undefined ? relevanceMeta(score) : null;
      const highlighted = highlightMatches(result.document, query);
      const metadataEntries = Object.entries(result.metadata ?? {}).filter(
        ([key]) => key !== 'source_type' && key !== 'sourceType'
      );

      return (
        <div
          key={result.id}
          className="bg-surface rounded-lg shadow-sm border border-border p-6 hover:shadow-md hover:border-primary/30 transition-all"
        >
          {/* Header: source badge + relevance */}
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${meta.color}`}
              >
                <Icon className="w-3.5 h-3.5" aria-hidden="true" />
                {meta.label}
              </span>
              <span className="text-sm font-medium text-muted">Result {index + 1}</span>
            </div>
            {relevance && (
              <span className={`rounded px-2 py-1 text-xs font-medium ${relevance.color}`}>
                {relevance.label}
              </span>
            )}
          </div>

          {/* Content with keyword highlighting */}
          <p className="text-text mb-4 leading-relaxed">{highlighted}</p>

          {/* Metadata tags */}
          {metadataEntries.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {metadataEntries.map(([key, value]) => (
                <span
                  key={key}
                  className="inline-flex items-center px-3 py-1 rounded-full text-xs bg-primary/20 text-primary font-medium"
                >
                  {key}: {String(value)}
                </span>
              ))}
            </div>
          )}
        </div>
      );
    })}
  </div>
);

export default SearchResultsList;
