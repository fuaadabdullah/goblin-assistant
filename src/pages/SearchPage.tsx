import React, { useState, useEffect } from 'react';
import { Search, FileText, ExternalLink, Loader2 } from 'lucide-react';
import { useToast } from '../contexts/ToastContext';

interface SearchResult {
  id: string;
  document: string;
  metadata?: Record<string, any>;
  distance?: number;
}

interface SearchResponse {
  results: SearchResult[];
  total_results: number;
}

const SearchPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [collections, setCollections] = useState<string[]>([]);
  const [selectedCollection, setSelectedCollection] = useState('documents');
  const [loadingCollections, setLoadingCollections] = useState(true);

  const { showError, showSuccess } = useToast();

  useEffect(() => {
    fetchCollections();
  }, []);

  const fetchCollections = async () => {
    try {
      setLoadingCollections(true);
      const response = await fetch('http://localhost:8000/search/collections');
      if (response.ok) {
        const data = await response.json();
        setCollections(data.collections);
      } else {
        throw new Error('Failed to load collections');
      }
    } catch (err) {
      console.error('Failed to fetch collections:', err);
      showError(
        'Failed to Load Collections',
        'Unable to connect to the search service. Please check your connection.'
      );
    } finally {
      setLoadingCollections(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8000/search/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query.trim(),
          collection_name: selectedCollection,
          n_results: 20,
        }),
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const data: SearchResponse = await response.json();
      setResults(data.results);
      showSuccess('Search Complete', `Found ${data.results.length} results`);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Search failed';
      setError(errorMessage);
      setResults([]);
      showError('Search Failed', errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleResultClick = (result: SearchResult) => {
    // In a real app, this might open a modal or navigate to a detail view
    console.log('Clicked result:', result);
  };

  const truncateText = (text: string, maxLength: number = 200) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">RAG Search</h1>
          <p className="text-gray-600">
            Search through your document collection using vector similarity
          </p>
        </div>

        {/* Search Form */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-1">
                <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-2">
                  Search Query
                </label>
                <div className="relative">
                  <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                  <input
                    id="query"
                    type="text"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    placeholder="Enter your search query..."
                    className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    disabled={loading}
                  />
                </div>
              </div>
              <div className="w-48">
                <label
                  htmlFor="collection"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Collection
                </label>
                <select
                  id="collection"
                  value={selectedCollection}
                  onChange={e => setSelectedCollection(e.target.value)}
                  className="w-full px-3 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={loading}
                >
                  {collections.map(collection => (
                    <option key={collection} value={collection}>
                      {collection}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Searching...
                </>
              ) : (
                <>
                  <Search className="h-5 w-5" />
                  Search Documents
                </>
              )}
            </button>
          </form>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">
                Search Results ({results.length})
              </h2>
            </div>

            <div className="space-y-3">
              {results.map((result, index) => (
                <div
                  key={result.id}
                  className="bg-white rounded-lg shadow-sm border p-4 hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => handleResultClick(result)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <FileText className="h-5 w-5 text-gray-400" />
                      <span className="text-sm font-medium text-gray-900">
                        Document {index + 1}
                      </span>
                    </div>
                    {result.distance && (
                      <span className="text-xs text-gray-500">
                        Distance: {result.distance.toFixed(4)}
                      </span>
                    )}
                  </div>

                  <p className="text-gray-700 mb-3 leading-relaxed">
                    {truncateText(result.document)}
                  </p>

                  {result.metadata && Object.keys(result.metadata).length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(result.metadata).map(([key, value]) => (
                        <span
                          key={key}
                          className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-gray-100 text-gray-800"
                        >
                          {key}: {String(value)}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="mt-3 flex items-center gap-2">
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        handleResultClick(result);
                      }}
                      className="text-blue-600 hover:text-blue-800 text-sm font-medium flex items-center gap-1"
                    >
                      <ExternalLink className="h-4 w-4" />
                      View Full Document
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* No Results */}
        {!loading && !error && results.length === 0 && query && (
          <div className="text-center py-12">
            <FileText className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No results found</h3>
            <p className="mt-1 text-sm text-gray-500">
              Try adjusting your search query or check if documents are indexed in the selected
              collection.
            </p>
          </div>
        )}

        {/* Initial State */}
        {!query && !loading && results.length === 0 && (
          <div className="text-center py-12">
            <Search className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">Search your documents</h3>
            <p className="mt-1 text-sm text-gray-500">
              Enter a query above to search through your vector database.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchPage;
