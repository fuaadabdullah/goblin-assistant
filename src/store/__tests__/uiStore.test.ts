import { renderHook, act } from '@testing-library/react';
import { useUIStore } from '../uiStore';

describe('UI Store (Zustand)', () => {
  beforeEach(() => {
    const { result } = renderHook(() => useUIStore());
    act(() => {
      result.current.resetUI();
    });
  });

  it('should have initial UI state', () => {
    const { result } = renderHook(() => useUIStore());
    expect(result.current.isSidebarOpen).toBeDefined();
    expect(result.current.isDarkMode).toBeDefined();
  });

  it('should toggle sidebar visibility', () => {
    const { result } = renderHook(() => useUIStore());
    const initialState = result.current.isSidebarOpen;

    act(() => {
      result.current.toggleSidebar();
    });

    expect(result.current.isSidebarOpen).toBe(!initialState);
  });

  it('should toggle dark mode', () => {
    const { result } = renderHook(() => useUIStore());
    const initialState = result.current.isDarkMode;

    act(() => {
      result.current.toggleDarkMode();
    });

    expect(result.current.isDarkMode).toBe(!initialState);
  });

  it('should set loading state', () => {
    const { result } = renderHook(() => useUIStore());

    act(() => {
      result.current.setLoading(true);
    });

    expect(result.current.isLoading).toBe(true);

    act(() => {
      result.current.setLoading(false);
    });

    expect(result.current.isLoading).toBe(false);
  });

  it('should open and close modal', () => {
    const { result } = renderHook(() => useUIStore());

    act(() => {
      result.current.openModal('test-modal');
    });

    expect(result.current.activeModal).toBe('test-modal');

    act(() => {
      result.current.closeModal();
    });

    expect(result.current.activeModal).toBeNull();
  });

  it('should reset UI state', () => {
    const { result } = renderHook(() => useUIStore());

    act(() => {
      result.current.setLoading(true);
      result.current.openModal('test-modal');
      result.current.resetUI();
    });

    // After reset, should return to initial state
    expect(result.current.isLoading).toBe(false);
    expect(result.current.activeModal).toBeNull();
  });
});
