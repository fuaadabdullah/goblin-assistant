import SearchHeader from './SearchHeader';
import SearchQuickQueries from './SearchQuickQueries';
import SearchForm from './SearchForm';
import SearchResultsList from './SearchResultsList';
import SearchEmptyState from './SearchEmptyState';
import type { SearchState } from '../hooks/useSearchResults';
import Seo from '../../../components/Seo';

interface SearchViewProps {
  /** Search state + handlers. */
  state: SearchState;
}

const SearchView = ({ state }: SearchViewProps) => (
  <div className="min-h-screen bg-bg py-12 px-4">
    <Seo title="Search" description="Audit gateway logs, trace provider routing, monitor costs and SLA compliance." robots="noindex,nofollow" />
    <main className="max-w-3xl mx-auto" id="main-content" tabIndex={-1} aria-label="Search">
      <SearchHeader
        title="Gateway Audit Log"
        subtitle="Search provider routing decisions, cost logs, and incident traces."
      />

      <SearchQuickQueries queries={state.quickQueries} onSelect={state.handleQuickQuery} />

      <SearchForm
        query={state.query}
        scope={state.scope}
        selectedCollection={state.selectedCollection}
        collectionsData={state.collectionsData}
        collectionsLoading={state.collectionsLoading}
        searching={state.searching}
        queryRef={state.queryRef}
        onQueryChange={state.setQuery}
        onScopeChange={state.setScope}
        onCollectionChange={state.setSelectedCollection}
        onSubmit={state.handleSearch}
        onClear={state.handleClear}
      />

      {state.error && (
        <div className="bg-surface border-2 border-danger rounded-lg p-4 mb-6 text-center">
          <p className="text-danger">{state.error}</p>
        </div>
      )}

      {!state.query && !state.searching && state.results.length === 0 && (
        <SearchEmptyState
          icon="🔍"
          title="Search everything"
          description="Enter a query above to search documents, messages, and tasks."
        />
      )}

      {!state.searching && !state.error && state.results.length === 0 && state.query && (
        <SearchEmptyState
          icon="📄"
          title="No results found"
          description="Try adjusting your search query or check if documents are indexed in the selected collection."
        />
      )}

      {!state.searching && state.results.length > 0 && <SearchResultsList results={state.results} />}
    </main>
  </div>
);

export default SearchView;
