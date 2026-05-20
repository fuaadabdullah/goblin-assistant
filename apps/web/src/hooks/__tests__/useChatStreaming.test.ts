import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useChatStreaming } from '../useChatStreaming';
import { apiClient } from '@/api';

const mockChatCompletion = jest.spyOn(apiClient, 'chatCompletion');

describe('useChatStreaming', () => {
  beforeEach(() => {
    mockChatCompletion.mockReset();
  });

  it('should initialize with loading false', () => {
    const { result } = renderHook(() => useChatStreaming({}));

    expect(result.current.isLoading).toBe(false);
  });

  it('should send a message and call callbacks', async () => {
    const onMessageStart = jest.fn();
    const onMessageUpdate = jest.fn();
    const onMessageComplete = jest.fn();

    mockChatCompletion.mockResolvedValue({
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

    mockChatCompletion.mockResolvedValue('Direct string response');

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

    mockChatCompletion.mockRejectedValue(
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
    let resolveResponse: ((value: { content: string }) => void) | null = null;
    mockChatCompletion.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveResponse = resolve;
        }),
    );

    const { result } = renderHook(() => useChatStreaming({}));

    let messagePromise: Promise<void>;
    act(() => {
      messagePromise = result.current.sendMessage('Test');
    });

    expect(result.current.isLoading).toBe(true);

    await act(async () => {
      resolveResponse?.({ content: 'test' });
      await messagePromise;
    });

    expect(result.current.isLoading).toBe(false);
  });

  it('should pass correct parameters to API', async () => {
    mockChatCompletion.mockResolvedValue({ content: 'Response' });

    const { result } = renderHook(() =>
      useChatStreaming({
        selectedModel: 'gpt-4o',
      }),
    );

    await act(async () => {
      await result.current.sendMessage('Hello world');
    });

    expect(mockChatCompletion).toHaveBeenCalledWith(
      [{ role: 'user', content: 'Hello world' }],
      'gpt-4o',
      true,
    );
  });

  it('should generate unique message IDs', async () => {
    mockChatCompletion.mockResolvedValue({ content: 'Response' });
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
