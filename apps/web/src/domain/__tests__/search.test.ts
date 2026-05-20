import type { SearchResult, SearchScope } from '../search';

describe('Search types', () => {
  it('creates a basic search result', () => {
    const result: SearchResult = {
      id: 'res1',
      document: 'This is a test document with content',
      score: 0.95,
    };
    expect(result.id).toBe('res1');
    expect(result.document).toBeDefined();
    expect(result.score).toBe(0.95);
  });

  it('creates search result with metadata', () => {
    const result: SearchResult = {
      id: 'res2',
      document: 'Another document',
      metadata: { source: 'web', tags: ['test'] },
      distance: 0.1,
    };
    expect(result.metadata?.source).toBe('web');
    expect(result.distance).toBe(0.1);
  });

  it('creates search result with score and distance', () => {
    const result: SearchResult = {
      id: 'res3',
      document: 'Document with both metrics',
      score: 0.85,
      distance: 0.15,
    };
    expect(result.score).toBe(0.85);
    expect(result.distance).toBe(0.15);
  });

  it('accepts valid SearchScope values', () => {
    const scope1: SearchScope = 'all';
    const scope2: SearchScope = 'documents';
    const scope3: SearchScope = 'messages';
    const scope4: SearchScope = 'tasks';
    expect(scope1).toBe('all');
    expect(scope2).toBe('documents');
    expect(scope3).toBe('messages');
    expect(scope4).toBe('tasks');
  });
});
