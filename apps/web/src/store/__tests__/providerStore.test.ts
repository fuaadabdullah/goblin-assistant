import { beforeEach, describe, expect, it } from 'vitest';
import { migrateLegacyProviderSelection, useProviderStore } from '../providerStore';

const STORAGE_KEY = 'goblin-provider-storage';

function resetStore(): void {
  useProviderStore.setState({ selectedProvider: '', selectedModel: '' });
}

describe('providerStore', () => {
  beforeEach(() => {
    localStorage.clear();
    resetStore();
  });

  it('starts with an empty selection', () => {
    expect(useProviderStore.getState().selectedProvider).toBe('');
    expect(useProviderStore.getState().selectedModel).toBe('');
  });

  it('setSelectedProvider normalizes provider ids and clears the model on change', () => {
    useProviderStore.getState().setSelectedProvider('azure-openai');
    expect(useProviderStore.getState().selectedProvider).toBe('azure_openai');

    useProviderStore.getState().setSelectedModel('gpt-4o');
    useProviderStore.getState().setSelectedProvider('openai');
    expect(useProviderStore.getState().selectedModel).toBe('');
  });

  it('setSelectedProvider keeps the model when the provider is unchanged', () => {
    useProviderStore.getState().setSelectedProvider('openai');
    useProviderStore.getState().setSelectedModel('gpt-4o');
    useProviderStore.getState().setSelectedProvider('openai');
    expect(useProviderStore.getState().selectedModel).toBe('gpt-4o');
  });

  it('persists the selection to localStorage', () => {
    useProviderStore.getState().setSelectedProvider('openai');
    useProviderStore.getState().setSelectedModel('gpt-4o');

    const raw = localStorage.getItem(STORAGE_KEY);
    expect(raw).not.toBeNull();
    const parsed = JSON.parse(raw as string) as {
      state: { selectedProvider: string; selectedModel: string };
    };
    expect(parsed.state.selectedProvider).toBe('openai');
    expect(parsed.state.selectedModel).toBe('gpt-4o');
  });

  it('migrates legacy localStorage keys once', () => {
    localStorage.setItem('selectedProvider', 'azure-openai');
    localStorage.setItem('selectedModel', 'gpt-4o');

    migrateLegacyProviderSelection();

    expect(useProviderStore.getState().selectedProvider).toBe('azure_openai');
    expect(useProviderStore.getState().selectedModel).toBe('gpt-4o');
    expect(localStorage.getItem('selectedProvider')).toBeNull();
    expect(localStorage.getItem('selectedModel')).toBeNull();
  });

  it('does not overwrite an existing selection during migration', () => {
    useProviderStore.getState().setSelectedProvider('openai');
    useProviderStore.getState().setSelectedModel('gpt-4o');
    localStorage.setItem('selectedProvider', 'anthropic');

    migrateLegacyProviderSelection();

    expect(useProviderStore.getState().selectedProvider).toBe('openai');
    expect(useProviderStore.getState().selectedModel).toBe('gpt-4o');
    expect(localStorage.getItem('selectedProvider')).toBeNull();
  });
});
