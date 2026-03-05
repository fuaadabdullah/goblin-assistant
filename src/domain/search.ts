export interface SearchResult {
  id: string;
  document: string;
  metadata?: Record<string, unknown>;
  distance?: number;
  score?: number;
}

export type SearchScope = 'all' | 'documents' | 'messages' | 'tasks';
