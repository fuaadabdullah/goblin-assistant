import { renderHook, act } from '@testing-library/react';

jest.mock('../../api', () => ({
  sendSupportMessage: jest.fn(),
}));
jest.mock('../../../../lib/ui-error', () => ({
  toUiError: jest.fn((_: unknown, opts: { userMessage: string }) => ({ userMessage: opts.userMessage })),
}));

import { useSupportForm } from '../useSupportForm';
import { sendSupportMessage } from '../../api';

const mockSend = sendSupportMessage as jest.Mock;

describe('useSupportForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });
  afterEach(() => jest.useRealTimers());

  it('returns initial state', () => {
    const { result } = renderHook(() => useSupportForm());
    expect(result.current.message).toBe('');
    expect(result.current.sent).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.sending).toBe(false);
  });

  it('setMessage updates message', () => {
    const { result } = renderHook(() => useSupportForm());
    act(() => result.current.setMessage('Help me'));
    expect(result.current.message).toBe('Help me');
  });

  it('handleSubmit does nothing for empty message', async () => {
    const { result } = renderHook(() => useSupportForm());
    const e = { preventDefault: jest.fn() } as unknown as React.FormEvent;
    await act(async () => { await result.current.handleSubmit(e); });
    expect(mockSend).not.toHaveBeenCalled();
  });

  it('handleSubmit does nothing for whitespace-only message', async () => {
    const { result } = renderHook(() => useSupportForm());
    act(() => result.current.setMessage('   '));
    const e = { preventDefault: jest.fn() } as unknown as React.FormEvent;
    await act(async () => { await result.current.handleSubmit(e); });
    expect(mockSend).not.toHaveBeenCalled();
  });

  it('handleSubmit sends message and clears it', async () => {
    mockSend.mockResolvedValue(undefined);
    const { result } = renderHook(() => useSupportForm());
    act(() => result.current.setMessage('Need help'));
    const e = { preventDefault: jest.fn() } as unknown as React.FormEvent;
    await act(async () => { await result.current.handleSubmit(e); });
    expect(mockSend).toHaveBeenCalledWith('Need help');
    expect(result.current.sent).toBe(true);
    expect(result.current.message).toBe('');
    expect(result.current.sending).toBe(false);
  });

  it('sent resets after timeout', async () => {
    mockSend.mockResolvedValue(undefined);
    const { result } = renderHook(() => useSupportForm());
    act(() => result.current.setMessage('test'));
    const e = { preventDefault: jest.fn() } as unknown as React.FormEvent;
    await act(async () => { await result.current.handleSubmit(e); });
    expect(result.current.sent).toBe(true);
    act(() => { jest.advanceTimersByTime(2500); });
    expect(result.current.sent).toBe(false);
  });

  it('sets error on failure', async () => {
    mockSend.mockRejectedValue(new Error('network'));
    const { result } = renderHook(() => useSupportForm());
    act(() => result.current.setMessage('test'));
    const e = { preventDefault: jest.fn() } as unknown as React.FormEvent;
    await act(async () => { await result.current.handleSubmit(e); });
    expect(result.current.error).toBe('We could not send your message. Please try again.');
    expect(result.current.sending).toBe(false);
  });

  it('prevents default on form event', async () => {
    mockSend.mockResolvedValue(undefined);
    const { result } = renderHook(() => useSupportForm());
    act(() => result.current.setMessage('msg'));
    const e = { preventDefault: jest.fn() } as unknown as React.FormEvent;
    await act(async () => { await result.current.handleSubmit(e); });
    expect(e.preventDefault).toHaveBeenCalled();
  });

  it('trims message before sending', async () => {
    mockSend.mockResolvedValue(undefined);
    const { result } = renderHook(() => useSupportForm());
    act(() => result.current.setMessage('  trimmed  '));
    const e = { preventDefault: jest.fn() } as unknown as React.FormEvent;
    await act(async () => { await result.current.handleSubmit(e); });
    expect(mockSend).toHaveBeenCalledWith('trimmed');
  });
});
