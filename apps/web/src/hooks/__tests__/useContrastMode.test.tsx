import { renderHook, act } from '@testing-library/react';
import { useContrastMode, ContrastModeProvider } from '../useContrastMode';
import React from 'react';

describe('useContrastMode Hook', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => React.createElement(ContrastModeProvider, { children });

    it('should provide contrast mode context', () => {
        const { result } = renderHook(() => useContrastMode(), { wrapper });
        expect(result.current).toBeDefined();
        expect(result.current.mode).toBe('dark');
    });

    it('should cycle through dark → light → high → dark', () => {
        const { result } = renderHook(() => useContrastMode(), { wrapper });
        expect(result.current.mode).toBe('dark');

        act(() => { result.current.toggleMode(); });
        expect(result.current.mode).toBe('light');

        act(() => { result.current.toggleMode(); });
        expect(result.current.mode).toBe('high');

        act(() => { result.current.toggleMode(); });
        expect(result.current.mode).toBe('dark');
    });

    it('should set specific mode', () => {
        const { result } = renderHook(() => useContrastMode(), { wrapper });

        act(() => { result.current.setMode('high'); });
        expect(result.current.mode).toBe('high');

        act(() => { result.current.setMode('light'); });
        expect(result.current.mode).toBe('light');

        act(() => { result.current.setMode('dark'); });
        expect(result.current.mode).toBe('dark');
    });
});
