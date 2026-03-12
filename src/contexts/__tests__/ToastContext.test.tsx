import React from 'react';
import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ToastProvider, useToast } from '../ToastContext';

// Test consumer component
function TestConsumer() {
  const { toasts, showSuccess, showError, showWarning, showInfo, removeToast, addToast } = useToast();
  return (
    <div>
      <span data-testid="count">{toasts.length}</span>
      {toasts.map(t => (
        <div key={t.id} data-testid={`toast-${t.id}`}>
          <span data-testid={`type-${t.id}`}>{t.type}</span>
          <span data-testid={`title-${t.id}`}>{t.title}</span>
          {t.message && <span data-testid={`msg-${t.id}`}>{t.message}</span>}
          <button onClick={() => removeToast(t.id)}>remove</button>
        </div>
      ))}
      <button data-testid="add-success" onClick={() => showSuccess('Done', 'It worked')}>success</button>
      <button data-testid="add-error" onClick={() => showError('Oops')}>error</button>
      <button data-testid="add-warning" onClick={() => showWarning('Careful', 'Watch out')}>warning</button>
      <button data-testid="add-info" onClick={() => showInfo('FYI')}>info</button>
      <button data-testid="add-no-auto" onClick={() => addToast({ type: 'info', title: 'Sticky', duration: 0 })}>sticky</button>
    </div>
  );
}

describe('ToastContext', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('throws when used outside provider', () => {
    const spy = jest.spyOn(console, 'error').mockImplementation(() => {});
    expect(() => render(<TestConsumer />)).toThrow('useToast must be used within a ToastProvider');
    spy.mockRestore();
  });

  it('starts with no toasts', () => {
    render(<ToastProvider><TestConsumer /></ToastProvider>);
    expect(screen.getByTestId('count').textContent).toBe('0');
  });

  it('showSuccess adds a success toast', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ToastProvider><TestConsumer /></ToastProvider>);
    await user.click(screen.getByTestId('add-success'));
    expect(screen.getByTestId('count').textContent).toBe('1');
    const toasts = screen.getAllByText('Done');
    expect(toasts.length).toBeGreaterThan(0);
  });

  it('showError adds an error toast', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ToastProvider><TestConsumer /></ToastProvider>);
    await user.click(screen.getByTestId('add-error'));
    expect(screen.getByTestId('count').textContent).toBe('1');
  });

  it('showWarning adds a warning toast', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ToastProvider><TestConsumer /></ToastProvider>);
    await user.click(screen.getByTestId('add-warning'));
    expect(screen.getByTestId('count').textContent).toBe('1');
  });

  it('showInfo adds an info toast', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ToastProvider><TestConsumer /></ToastProvider>);
    await user.click(screen.getByTestId('add-info'));
    expect(screen.getByTestId('count').textContent).toBe('1');
  });

  it('removeToast removes a toast', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ToastProvider><TestConsumer /></ToastProvider>);
    await user.click(screen.getByTestId('add-success'));
    expect(screen.getByTestId('count').textContent).toBe('1');
    await user.click(screen.getByText('remove'));
    expect(screen.getByTestId('count').textContent).toBe('0');
  });

  it('auto-removes toast after duration', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ToastProvider><TestConsumer /></ToastProvider>);
    await user.click(screen.getByTestId('add-success'));
    expect(screen.getByTestId('count').textContent).toBe('1');
    act(() => { jest.advanceTimersByTime(6000); });
    expect(screen.getByTestId('count').textContent).toBe('0');
  });

  it('does not auto-remove toast with duration 0', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ToastProvider><TestConsumer /></ToastProvider>);
    await user.click(screen.getByTestId('add-no-auto'));
    expect(screen.getByTestId('count').textContent).toBe('1');
    act(() => { jest.advanceTimersByTime(30000); });
    expect(screen.getByTestId('count').textContent).toBe('1');
  });

  it('supports multiple toasts', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ToastProvider><TestConsumer /></ToastProvider>);
    await user.click(screen.getByTestId('add-success'));
    await user.click(screen.getByTestId('add-error'));
    await user.click(screen.getByTestId('add-info'));
    expect(screen.getByTestId('count').textContent).toBe('3');
  });

  it('toast includes message when provided', async () => {
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });
    render(<ToastProvider><TestConsumer /></ToastProvider>);
    await user.click(screen.getByTestId('add-warning'));
    expect(screen.getByText('Watch out')).toBeInTheDocument();
  });
});
