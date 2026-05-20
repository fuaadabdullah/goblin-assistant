import type { SearchResult } from '../types';

interface SearchResultsListProps {
  /** Search results to render. */
  results: SearchResult[];
}

const SearchResultsList = ({ results }: SearchResultsListProps) => (
  <div className="space-y-4">
    <h2 className="text-xl font-semibold text-text mb-4">
      Search Results ({results.length})
    </h2>
    {results.map((result, index) => (
      <div
        key={result.id}
        className="bg-surface rounded-lg shadow-sm border border-border p-6 hover:shadow-md transition-shadow"
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xl">📄</span>
            <span className="text-sm font-medium text-text">Result {index + 1}</span>
          </div>
          {result.score !== undefined ? (
            <span className="text-xs text-muted bg-surface-hover px-2 py-1 rounded">
              Score: {result.score.toFixed(4)}
            </span>
          ) : result.distance !== undefined ? (
            <span className="text-xs text-muted bg-surface-hover px-2 py-1 rounded">
              Distance: {result.distance.toFixed(4)}
            </span>
          ) : null}
        </div>
        <p className="text-text mb-4 leading-relaxed">{result.document}</p>
        {result.metadata && Object.keys(result.metadata).length > 0 && (
          <div className="flex flex-wrap gap-2">
            {Object.entries(result.metadata).map(([key, value]) => (
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
    ))}
  </div>
);

export default SearchResultsList;
