import type { FormEvent, RefObject } from 'react';
import type { SearchScope } from '../types';

interface SearchFormProps {
  /** Current query string. */
  query: string;
  /** Current search scope. */
  scope: SearchScope;
  /** Currently selected collection. */
  selectedCollection: string;
  /** Available collections to search within. */
  collectionsData: string[] | undefined;
  /** Whether collections are loading. */
  collectionsLoading: boolean;
  /** Whether a search is in progress. */
  searching: boolean;
  /** Input ref for focus. */
  queryRef: RefObject<HTMLInputElement>;
  /** Update query string. */
  onQueryChange: (value: string) => void;
  /** Update scope selection. */
  onScopeChange: (value: SearchScope) => void;
  /** Update collection selection. */
  onCollectionChange: (value: string) => void;
  /** Submit handler. */
  onSubmit: (e: FormEvent) => void;
  /** Clear handler. */
  onClear: () => void;
}

const SearchForm = ({
  query,
  scope,
  selectedCollection,
  collectionsData,
  collectionsLoading,
  searching,
  queryRef,
  onQueryChange,
  onScopeChange,
  onCollectionChange,
  onSubmit,
  onClear,
}: SearchFormProps) => (
  <div className="bg-surface rounded-xl shadow-sm border border-border p-8 mb-8">
    <form onSubmit={onSubmit} className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-text mb-2">Search Scope</label>
        <div className="flex flex-wrap gap-2">
          {[
            { value: 'all', label: 'Everything' },
            { value: 'documents', label: 'Documents' },
            { value: 'messages', label: 'Messages' },
            { value: 'tasks', label: 'Tasks' },
          ].map(item => (
            <button
              key={item.value}
              type="button"
              onClick={() => onScopeChange(item.value as SearchScope)}
              className={`px-3 py-2 rounded-full text-sm border transition-colors ${
                scope === item.value
                  ? 'bg-primary text-text-inverse border-primary shadow-glow-primary'
                  : 'bg-surface-hover text-text border-border hover:bg-surface-active'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
        <p className="text-xs text-muted mt-2">
          Use Everything for broad results or narrow to one category.
        </p>
      </div>

      <div>
        <label htmlFor="query" className="block text-sm font-medium text-text mb-2">
          Search Query
        </label>
        <input
          id="query"
          type="text"
          value={query}
          onChange={e => onQueryChange(e.target.value)}
          placeholder="Search by question or keyword..."
          ref={queryRef}
          className="w-full px-4 py-3 border border-border bg-surface-hover rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-text placeholder-muted"
          disabled={searching}
        />
        <p className="text-xs text-muted mt-2">
          Tip: include context like a person, date, or project name.
        </p>
      </div>

      <div>
        <label htmlFor="collection" className="block text-sm font-medium text-text mb-2">
          Collection
        </label>
        <select
          id="collection"
          value={selectedCollection}
          onChange={e => onCollectionChange(e.target.value)}
          className="w-full px-4 py-3 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-surface-hover text-text"
          disabled={collectionsLoading || searching}
        >
          {(collectionsData || []).map(name => {
            return (
              <option key={name} value={name}>
                {name}
              </option>
            );
          })}
        </select>
      </div>

      <button
        type="submit"
        disabled={searching || !query.trim() || !selectedCollection}
        className="w-full bg-primary text-text-inverse py-3 px-6 rounded-lg hover:brightness-110 focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-glow-primary transition-all flex items-center justify-center gap-2"
      >
        {searching ? (
          <>
            <span className="animate-spin">🔄</span>
            Searching...
          </>
        ) : (
          <>
            <span>🔍</span>
            Search Everything
          </>
        )}
      </button>
      <button
        type="button"
        onClick={onClear}
        className="w-full bg-surface-hover text-text py-3 px-6 rounded-lg border border-border hover:bg-surface-active transition-all font-medium"
      >
        Clear Search
      </button>
    </form>
  </div>
);

export default SearchForm;
