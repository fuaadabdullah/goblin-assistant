import { renderHook, act } from '@testing-library/react';
import { useUIStore } from '../uiStore';

describe('UI Store (Zustand)', () => {
  it('should have initial UI state', () => {
    const { result } = renderHook(() => useUIStore());
    expect(result.current.sidebarOpen).toBeDefined();
    expect(result.current.highContrast).toBeDefined();
    expect(result.current.currentTheme).toBeDefined();
    expect(result.current.activeModal).toBeNull();
    expect(result.current.notifications).toEqual([]);
  });

  it('should toggle sidebar visibility', () => {
    const { result } = renderHook(() => useUIStore());
    const initial = result.current.sidebarOpen;
    act(() => { result.current.toggleSidebar(); });
    expect(result.current.sidebarOpen).toBe(!initial);
  });

  it('should set sidebar open', () => {
    const { result } = renderHook(() => useUIStore());
    act(() => { result.current.setSidebarOpen(false); });
    expect(result.current.sidebarOpen).toBe(false);
    act(() => { result.current.setSidebarOpen(true); });
    expect(result.current.sidebarOpen).toBe(true);
  });

  it('should toggle chat sidebar', () => {
    const { result } = renderHook(() => useUIStore());
    const initial = result.current.chatSidebarOpen;
    act(() => { result.current.toggleChatSidebar(); });
    expect(result.current.chatSidebarOpen).toBe(!initial);
  });

  it('should open and close modal', () => {
    const { result } = renderHook(() => useUIStore());
    act(() => { result.current.openModal('test-modal'); });
    expect(result.current.activeModal).toBe('test-modal');
    act(() => { result.current.closeModal(); });
    expect(result.current.activeModal).toBeNull();
  });

  it('should set high contrast mode', () => {
    const { result } = renderHook(() => useUIStore());
    act(() => { result.current.setHighContrast(true); });
    expect(result.current.highContrast).toBe(true);
    act(() => { result.current.setHighContrast(false); });
    expect(result.current.highContrast).toBe(false);
  });

  it('should set theme', () => {
    const { result } = renderHook(() => useUIStore());
    act(() => { result.current.setTheme('nocturne'); });
    expect(result.current.currentTheme).toBe('nocturne');
    act(() => { result.current.setTheme('default'); });
    expect(result.current.currentTheme).toBe('default');
  });

  it('should add and remove notifications', () => {
    const { result } = renderHook(() => useUIStore());
    act(() => {
      result.current.addNotification({ type: 'success', title: 'Test' });
    });
    expect(result.current.notifications.length).toBeGreaterThanOrEqual(1);
    const id = result.current.notifications[0].id;
    act(() => { result.current.removeNotification(id); });
  });
});
