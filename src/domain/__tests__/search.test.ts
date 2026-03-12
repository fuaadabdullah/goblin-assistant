import type { SearchResult, SearchScope } from '../search';

describe('domain/search types', () => {
  it('should build a SearchResult with required fields', () => {
    const result: SearchResult = { id: 's1', document: 'Hello world' };
    expect(result.id).toBe('s1');
    expect(result.document).toBe('Hello world');
    expect(result.metadata).toBeUndefined();
    expect(result.distance).toBeUndefined();
    expect(result.score).toBeUndefined();
  });

  it('should build a SearchResult with optional fields', () => {
    const result: SearchResult = {
      id: 's2',
      document: 'Test doc',
      metadata: { source: 'wiki' },
      distance: 0.5,
      score: 0.95,
    };
    expect(result.metadata).toEqual({ source: 'wiki' });
    expect(result.distance).toBe(0.5);
    expect(result.score).toBe(0.95);
  });

  it('should accept all SearchScope values', () => {
    const scopes: SearchScope[] = ['all', 'documents', 'messages', 'tasks'];
    expect(scopes).toHaveLength(4);
  });
});
