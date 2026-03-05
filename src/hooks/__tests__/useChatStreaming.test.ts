import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { renderHook, act } from '@testing-library/react';
import { useChatStreaming } from '../useChatStreaming';

// Mock the API client
jest.mock('../../api/apiClient', () => ({
  apiClient: {
    chatCompletion: jest.fn(),
  },
}));

const mockApiClient = require('../../api/apiClient').apiClient;

describe('useChatStreaming', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should initialize with loading false', () => {
    const { result } = renderHook(() => useChatStreaming({}));

    expect(result.current.isLoading).toBe(false);
  });

  it('should send a message and call callbacks', async () => {
    const onMessageStart = jest.fn();
    const onMessageUpdate = jest.fn();
    const onMessageComplete = jest.fn();

    mockApiClient.chatCompletion.mockResolvedValue({
      content: 'Hello! How can I help?',
    });

    const { result } = renderHook(() =>
      useChatStreaming({
        onMessageStart,
        onMessageUpdate,
        onMessageComplete,
        selectedProvider: 'openai',
        selectedModel: 'gpt-4o-mini',
        demoMode: false,
      }),
    );

    await act(async () => {
      await result.current.sendMessage('Hello');
    });

    expect(onMessageStart).toHaveBeenCalled();
    expect(onMessageUpdate).toHaveBeenCalled();
    expect(onMessageComplete).toHaveBeenCalled();
    expect(result.current.isLoading).toBe(false);
  });

  it('should handle string responses', async () => {
    const onMessageComplete = jest.fn();

    mockApiClient.chatCompletion.mockResolvedValue('Direct string response');

    const { result } = renderHook(() =>
      useChatStreaming({
        onMessageComplete,
      }),
    );

    await act(async () => {
      await result.current.sendMessage('Test');
    });

    expect(onMessageComplete).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        content: 'Direct string response',
      }),
    );
  });

  it('should handle API errors gracefully', async () => {
    const onError = jest.fn();

    mockApiClient.chatCompletion.mockRejectedValue(
      new Error('API request failed'),
    );

    const { result } = renderHook(() =>
      useChatStreaming({
        onError,
      }),
    );

    await act(async () => {
      await result.current.sendMessage('Test');
    });

    expect(onError).toHaveBeenCalledWith('Chat error', 'API request failed');
  });

  it('should set loading state during request', async () => {
    mockApiClient.chatCompletion.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(() => resolve({ content: 'test' }), 100),
        ),
    );

    const { result } = renderHook(() => useChatStreaming({}));

    const messagePromise = act(async () => {
      await result.current.sendMessage('Test');
    });

    // Initially loading
    expect(result.current.isLoading).toBe(true);

    await messagePromise;

    // After completion
    expect(result.current.isLoading).toBe(false);
  });

  it('should pass correct parameters to API', async () => {
    mockApiClient.chatCompletion.mockResolvedValue({ content: 'Response' });

    const { result } = renderHook(() =>
      useChatStreaming({
        selectedModel: 'gpt-4o',
      }),
    );

    await act(async () => {
      await result.current.sendMessage('Hello world');
    });

    expect(mockApiClient.chatCompletion).toHaveBeenCalledWith(
      [{ role: 'user', content: 'Hello world' }],
      'gpt-4o',
      true,
    );
  });

  it('should generate unique message IDs', async () => {
    mockApiClient.chatCompletion.mockResolvedValue({ content: 'Response' });
    const messageIds = new Set<string>();
    const onMessageStart = jest.fn((id: string) => messageIds.add(id));

    const { result } = renderHook(() =>
      useChatStreaming({
        onMessageStart,
      }),
    );

    await act(async () => {
      await result.current.sendMessage('Message 1');
    });

    await act(async () => {
      await result.current.sendMessage('Message 2');
    });

    expect(messageIds.size).toBe(2);
  });
});
