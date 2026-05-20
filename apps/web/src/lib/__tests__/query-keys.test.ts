import { queryKeys } from '../query-keys';

describe('query-keys', () => {
  it('exposes static health keys', () => {
    expect(queryKeys.health).toEqual(['health']);
    expect(queryKeys.streamingHealth).toEqual(['health', 'streaming']);
    expect(queryKeys.allHealth).toEqual(['health', 'all']);
  });

  it('exposes static chat keys', () => {
    expect(queryKeys.models).toEqual(['chat', 'models']);
    expect(queryKeys.routingInfo).toEqual(['chat', 'routing-info']);
    expect(queryKeys.chatThreads).toEqual(['chat', 'threads']);
  });

  it('generates chatConversation key from id', () => {
    expect(queryKeys.chatConversation('abc')).toEqual(['chat', 'conversation', 'abc']);
  });

  it('exposes static search keys', () => {
    expect(queryKeys.collections).toEqual(['search', 'collections']);
  });

  it('generates searchResults key with defaults', () => {
    expect(queryKeys.searchResults('col1', 'hello')).toEqual(['search', 'results', 'col1', 'hello', 8]);
  });

  it('generates searchResults key with custom limit', () => {
    expect(queryKeys.searchResults('col1', 'hello', 20)).toEqual(['search', 'results', 'col1', 'hello', 20]);
  });

  it('exposes static settings keys', () => {
    expect(queryKeys.providers).toEqual(['settings', 'providers']);
    expect(queryKeys.credentials).toEqual(['settings', 'credentials']);
    expect(queryKeys.modelConfigs).toEqual(['settings', 'models']);
    expect(queryKeys.globalSettings).toEqual(['settings', 'global']);
  });

  it('exposes auth key', () => {
    expect(queryKeys.authValidate).toEqual(['auth', 'validate']);
  });

  it('generates routingProviders key with/without capability', () => {
    expect(queryKeys.routingProviders()).toEqual(['routing', 'providers']);
    expect(queryKeys.routingProviders('chat')).toEqual(['routing', 'providers', 'chat']);
  });

  it('exposes routing health key', () => {
    expect(queryKeys.routingHealth).toEqual(['routing', 'health']);
  });

  it('exposes goblins keys', () => {
    expect(queryKeys.goblins).toEqual(['goblins']);
    expect(queryKeys.goblinHistory('g1', 10)).toEqual(['goblins', 'g1', 'history', 10]);
    expect(queryKeys.goblinStats('g1')).toEqual(['goblins', 'g1', 'stats']);
  });

  it('exposes RAPTOR keys', () => {
    expect(queryKeys.raptorStatus).toEqual(['raptor', 'status']);
    expect(queryKeys.raptorLogs(50)).toEqual(['raptor', 'logs', 50]);
    expect(queryKeys.raptorLogs()).toEqual(['raptor', 'logs', undefined]);
  });

  it('exposes sandbox keys', () => {
    expect(queryKeys.sandboxJobs).toEqual(['sandbox', 'jobs']);
    expect(queryKeys.jobLogs('j1')).toEqual(['sandbox', 'jobs', 'j1', 'logs']);
    expect(queryKeys.jobArtifacts('j1')).toEqual(['sandbox', 'jobs', 'j1', 'artifacts']);
  });
});
