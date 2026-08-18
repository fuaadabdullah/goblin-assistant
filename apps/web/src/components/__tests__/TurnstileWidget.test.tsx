import { act, render, renderHook, waitFor } from '@testing-library/react';
import TurnstileWidget, { useTurnstile } from '../TurnstileWidget';

const { mockDevError, mockDevWarn } = vi.hoisted(() => ({
  mockDevError: vi.fn(),
  mockDevWarn: vi.fn(),
}));

vi.mock('@/utils/dev-log', () => ({
  devError: mockDevError,
  devWarn: mockDevWarn,
}));

describe('TurnstileWidget Component', () => {
  const renderMock = vi.fn();
  const removeMock = vi.fn();
  const resetMock = vi.fn();
  const executeMock = vi.fn();

  const installTurnstile = () => {
    (window as any).turnstile = {
      render: renderMock,
      reset: resetMock,
      remove: removeMock,
      execute: executeMock,
      getResponse: vi.fn(),
    };
  };

  beforeEach(() => {
    document.head
      .querySelectorAll('script[src*="challenges.cloudflare.com/turnstile"]')
      .forEach((node) => node.remove());
    document.body.querySelectorAll('div[style*="display: none"]').forEach((node) => node.remove());
    vi.clearAllMocks();
    installTurnstile();
  });

  afterEach(() => {
    delete (window as any).turnstile;
  });

  it('loads, renders, and cleans up the managed widget', async () => {
    const onVerify = vi.fn();
    const onError = vi.fn();

    renderMock.mockImplementation((_element, options) => {
      options.callback('managed-token');
      return 'widget-managed';
    });

    const { unmount } = render(
      <TurnstileWidget siteKey="test-site-key" onVerify={onVerify} onError={onError} />
    );

    const script = await waitFor(
      () =>
        document.head.querySelector(
          'script[src*="challenges.cloudflare.com/turnstile"]'
        ) as HTMLScriptElement | null
    );

    expect(script).not.toBeNull();

    await act(async () => {
      script?.onload?.(new Event('load'));
    });

    await waitFor(() => expect(renderMock).toHaveBeenCalledTimes(1));

    const [, options] = renderMock.mock.calls[0] as [HTMLElement, any];
    options.callback('verified-token');
    options['error-callback']();
    options['expired-callback']();

    expect(onVerify).toHaveBeenCalledWith('managed-token');
    expect(onVerify).toHaveBeenCalledWith('verified-token');
    expect(onError).toHaveBeenCalledWith('Bot verification failed');
    expect(onError).toHaveBeenCalledWith('Verification expired, please try again');
    expect(mockDevError).toHaveBeenCalledWith('Turnstile verification failed');
    expect(mockDevWarn).toHaveBeenCalledWith('Turnstile token expired');

    unmount();
    expect(removeMock).toHaveBeenCalledWith('widget-managed');
  });

  it('supports the invisible hook flow and reset', async () => {
    const existingScript = document.createElement('script');
    existingScript.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
    document.head.appendChild(existingScript);

    renderMock.mockImplementation((container, options) => {
      options.callback('rendered-token');
      return 'widget-invisible';
    });
    executeMock.mockImplementation((_widgetId, options) => {
      options?.callback?.('executed-token');
    });

    const { result, unmount } = renderHook(() => useTurnstile('site-key'));

    await waitFor(() => expect(renderMock).toHaveBeenCalledTimes(1));
    expect((renderMock.mock.calls[0] as [HTMLElement, any])[0]).toHaveStyle({
      display: 'none',
    });
    await waitFor(() => expect(result.current.token).toBe('rendered-token'));

    await expect(result.current.execute()).resolves.toBe('executed-token');
    expect(executeMock).toHaveBeenCalledWith('widget-invisible', expect.any(Object));

    act(() => {
      result.current.reset();
    });

    expect(resetMock).toHaveBeenCalledWith('widget-invisible');
    await waitFor(() => expect(result.current.token).toBe(''));

    unmount();
    expect(removeMock).toHaveBeenCalledWith('widget-invisible');
  });

  it('reports a script load failure', async () => {
    const onError = vi.fn();

    render(<TurnstileWidget siteKey="test-site-key" onVerify={vi.fn()} onError={onError} />);

    const script = await waitFor(
      () =>
        document.head.querySelector(
          'script[src*="challenges.cloudflare.com/turnstile"]'
        ) as HTMLScriptElement | null
    );

    act(() => {
      script?.onerror?.(new Event('error'));
    });

    expect(mockDevError).toHaveBeenCalledWith('Failed to load Turnstile script');
    expect(onError).toHaveBeenCalledWith('Failed to load bot protection');
  });
});
