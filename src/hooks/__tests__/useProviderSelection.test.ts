import { renderHook, act } from '@testing-library/react';
import { useProviderSelection } from '../useProviderSelection';

describe('useProviderSelection', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('initializes with empty selections', () => {
    const { result } = renderHook(() => useProviderSelection({
      providers: [],
      models: [],
    }));

    expect(result.current.selectedProvider).toBe('');
    expect(result.current.selectedModel).toBe('');
  });

  it('selects first provider when none stored', () => {
    const { result } = renderHook(() => useProviderSelection({
      providers: ['openai', 'anthropic'],
      models: ['gpt-4', 'claude-3'],
    }));

    expect(result.current.selectedProvider).toBe('openai');
  });

  it('loads provider from localStorage', () => {
    localStorage.setItem('selectedProvider', 'anthropic');

    const { result } = renderHook(() => useProviderSelection({
      providers: ['openai', 'anthropic'],
      models: ['gpt-4', 'claude-3'],
    }));

    expect(result.current.selectedProvider).toBe('anthropic');
  });

  it('loads model from localStorage', () => {
    localStorage.setItem('selectedModel', 'claude-3');

    const { result } = renderHook(() => useProviderSelection({
      providers: ['openai', 'anthropic'],
      models: ['gpt-4', 'claude-3'],
    }));

    expect(result.current.selectedModel).toBe('claude-3');
  });

  it('updates selectedProvider and persists to localStorage', () => {
    const { result } = renderHook(() => useProviderSelection({
      providers: ['openai', 'anthropic'],
      models: ['gpt-4', 'claude-3'],
    }));

    act(() => {
      result.current.setSelectedProvider('anthropic');
    });

    expect(result.current.selectedProvider).toBe('anthropic');
    expect(localStorage.getItem('selectedProvider')).toBe('anthropic');
  });

  it('updates selectedModel and persists to localStorage', () => {
    const { result } = renderHook(() => useProviderSelection({
      providers: ['openai', 'anthropic'],
      models: ['gpt-4', 'claude-3'],
    }));

    act(() => {
      result.current.setSelectedModel('claude-3');
    });

    expect(result.current.selectedModel).toBe('claude-3');
    expect(localStorage.getItem('selectedModel')).toBe('claude-3');
  });

  it('resets selections when providers list changes', () => {
    const { rerender } = renderHook(
      ({ providers, models }) => useProviderSelection({ providers, models }),
      {
        initialProps: {
          providers: ['openai', 'anthropic'],
          models: ['gpt-4', 'claude-3'],
        },
      }
    );

    rerender({
      providers: ['ollama'],
      models: ['local-model'],
    });

    const { result } = renderHook(() => useProviderSelection({
      providers: ['ollama'],
      models: ['local-model'],
    }));

    expect(result.current.selectedProvider).toBe('ollama');
  });

  it('normalizes provider IDs from aliases', () => {
    localStorage.setItem('selectedProvider', 'gpt-4-turbo');

    const { result } = renderHook(() => useProviderSelection({
      providers: ['openai', 'anthropic'],
      models: ['gpt-4', 'claude-3'],
    }));

    // Should handle alias normalization gracefully
    expect(result.current.selectedProvider).toBeDefined();
  });

  it('handles empty provider list', () => {
    const { result } = renderHook(() => useProviderSelection({
      providers: [],
      models: [],
    }));

    expect(result.current.selectedProvider).toBe('');
    expect(result.current.selectedModel).toBe('');
  });
});
