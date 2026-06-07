import React from 'react';
import { render, screen, act, fireEvent } from '@testing-library/react';
import { useUIStore } from '../../store/uiStore';
import { useToast } from '../useToast';

function TestConsumer() {
  const { toasts, showSuccess, showError, showWarning, showInfo, removeToast, addToast } =
    useToast();
  return (
    <div>
      <span data-testid="count">{toasts.length}</span>
      {toasts.map((t) => (
        <div key={t.id} data-testid={`toast-${t.id}`}>
          <span data-testid={`type-${t.id}`}>{t.type}</span>
          <span data-testid={`title-${t.id}`}>{t.title}</span>
          {t.message && <span data-testid={`msg-${t.id}`}>{t.message}</span>}
          <button onClick={() => removeToast(t.id)}>remove</button>
        </div>
      ))}
      <button data-testid="add-success" onClick={() => showSuccess('Done', 'It worked')}>
        success
      </button>
      <button data-testid="add-error" onClick={() => showError('Oops')}>
        error
      </button>
      <button data-testid="add-warning" onClick={() => showWarning('Careful', 'Watch out')}>
        warning
      </button>
      <button data-testid="add-info" onClick={() => showInfo('FYI')}>
        info
      </button>
      <button
        data-testid="add-no-auto"
        onClick={() => addToast({ type: 'info', title: 'Sticky', duration: 0 })}
      >
        sticky
      </button>
    </div>
  );
}

describe('useToast', () => {
  beforeEach(() => {
    useUIStore.setState({ toasts: [] });
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts with no toasts', () => {
    render(<TestConsumer />);
    expect(screen.getByTestId('count').textContent).toBe('0');
  });

  it('showSuccess adds a success toast', () => {
    render(<TestConsumer />);
    act(() => { fireEvent.click(screen.getByTestId('add-success')); });
    expect(screen.getByTestId('count').textContent).toBe('1');
    expect(screen.getAllByText('Done').length).toBeGreaterThan(0);
  });

  it('showError adds an error toast', () => {
    render(<TestConsumer />);
    act(() => { fireEvent.click(screen.getByTestId('add-error')); });
    expect(screen.getByTestId('count').textContent).toBe('1');
  });

  it('showWarning adds a warning toast', () => {
    render(<TestConsumer />);
    act(() => { fireEvent.click(screen.getByTestId('add-warning')); });
    expect(screen.getByTestId('count').textContent).toBe('1');
  });

  it('showInfo adds an info toast', () => {
    render(<TestConsumer />);
    act(() => { fireEvent.click(screen.getByTestId('add-info')); });
    expect(screen.getByTestId('count').textContent).toBe('1');
  });

  it('removeToast removes a toast', () => {
    render(<TestConsumer />);
    act(() => { fireEvent.click(screen.getByTestId('add-success')); });
    expect(screen.getByTestId('count').textContent).toBe('1');
    act(() => { fireEvent.click(screen.getByText('remove')); });
    expect(screen.getByTestId('count').textContent).toBe('0');
  });

  it('auto-removes toast after duration', () => {
    render(<TestConsumer />);
    act(() => { fireEvent.click(screen.getByTestId('add-success')); });
    expect(screen.getByTestId('count').textContent).toBe('1');
    act(() => { vi.advanceTimersByTime(6000); });
    expect(screen.getByTestId('count').textContent).toBe('0');
  });

  it('does not auto-remove toast with duration 0', () => {
    render(<TestConsumer />);
    act(() => { fireEvent.click(screen.getByTestId('add-no-auto')); });
    expect(screen.getByTestId('count').textContent).toBe('1');
    act(() => { vi.advanceTimersByTime(30000); });
    expect(screen.getByTestId('count').textContent).toBe('1');
  });

  it('supports multiple toasts', () => {
    render(<TestConsumer />);
    act(() => { fireEvent.click(screen.getByTestId('add-success')); });
    act(() => { fireEvent.click(screen.getByTestId('add-error')); });
    act(() => { fireEvent.click(screen.getByTestId('add-info')); });
    expect(screen.getByTestId('count').textContent).toBe('3');
  });

  it('toast includes message when provided', () => {
    render(<TestConsumer />);
    act(() => { fireEvent.click(screen.getByTestId('add-warning')); });
    expect(screen.getByText('Watch out')).toBeInTheDocument();
  });
});
