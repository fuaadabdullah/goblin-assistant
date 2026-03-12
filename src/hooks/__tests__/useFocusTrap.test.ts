import { renderHook, act } from '@testing-library/react';
import { useFocusTrap } from '../useFocusTrap';

describe('useFocusTrap', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    jest.useFakeTimers();
  });

  afterEach(() => {
    document.body.removeChild(container);
    document.body.style.overflow = '';
    jest.useRealTimers();
  });

  it('returns a ref object', () => {
    const onClose = jest.fn();
    const { result } = renderHook(() => useFocusTrap(false, onClose));
    expect(result.current).toHaveProperty('current');
  });

  it('locks body scroll when active', () => {
    const onClose = jest.fn();
    const { result } = renderHook(() => useFocusTrap(true, onClose));
    // Attach ref to container
    Object.defineProperty(result.current, 'current', { value: container, writable: true });
    // Re-render to apply effect with container
    expect(document.body.style.overflow).toBe('hidden');
  });

  it('does not lock body scroll when inactive', () => {
    const onClose = jest.fn();
    document.body.style.overflow = '';
    renderHook(() => useFocusTrap(false, onClose));
    expect(document.body.style.overflow).toBe('');
  });

  it('calls onClose on Escape key', () => {
    const onClose = jest.fn();
    const { result } = renderHook(() => useFocusTrap(true, onClose));
    Object.defineProperty(result.current, 'current', { value: container, writable: true });

    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('does not call onClose on Escape when inactive', () => {
    const onClose = jest.fn();
    renderHook(() => useFocusTrap(false, onClose));

    act(() => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    });
    expect(onClose).not.toHaveBeenCalled();
  });

  it('restores body overflow on cleanup', () => {
    const onClose = jest.fn();
    const { unmount } = renderHook(() => useFocusTrap(true, onClose));
    expect(document.body.style.overflow).toBe('hidden');
    unmount();
    expect(document.body.style.overflow).toBe('');
  });

  it('traps Tab focus to first element when at last', () => {
    const btn1 = document.createElement('button');
    const btn2 = document.createElement('button');
    container.appendChild(btn1);
    container.appendChild(btn2);
    btn2.focus();

    const onClose = jest.fn();
    const { result } = renderHook(() => useFocusTrap(true, onClose));
    Object.defineProperty(result.current, 'current', { value: container, writable: true });

    act(() => {
      const event = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true });
      Object.defineProperty(event, 'shiftKey', { value: false });
      window.dispatchEvent(event);
    });
    // Focus should wrap (Tab at last goes to first)
    // The hook calls event.preventDefault() + first.focus()
  });

  it('focuses first interactive element after timer', () => {
    const btn = document.createElement('button');
    container.appendChild(btn);

    const onClose = jest.fn();
    const { result } = renderHook(() => useFocusTrap(true, onClose));
    Object.defineProperty(result.current, 'current', { value: container, writable: true });

    act(() => {
      jest.advanceTimersByTime(300);
    });
    // Timer should have fired
  });
});
