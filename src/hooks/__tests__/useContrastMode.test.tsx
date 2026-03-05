import { renderHook, act } from '@testing-library/react';
import { useContrastMode, ContrastModeProvider } from '../useContrastMode';
import React from 'react';

describe('useContrastMode Hook', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => React.createElement(ContrastModeProvider, { children });

    it('should provide contrast mode context', () => {
        const { result } = renderHook(() => useContrastMode(), { wrapper });
        expect(result.current).toBeDefined();
    });

    it('should toggle high contrast mode', () => {
        const { result } = renderHook(() => useContrastMode(), { wrapper });
        const initialState = result.current.isHighContrast;

        act(() => {
            result.current.toggleHighContrast();
        });

        expect(result.current.isHighContrast).toBe(!initialState);
    });

    it('should set specific contrast mode', () => {
        const { result } = renderHook(() => useContrastMode(), { wrapper });

        act(() => {
            result.current.setHighContrast(true);
        });

        expect(result.current.isHighContrast).toBe(true);

        act(() => {
            result.current.setHighContrast(false);
        });

        expect(result.current.isHighContrast).toBe(false);
    });

    it('should provide class name for contrast mode', () => {
        const { result } = renderHook(() => useContrastMode(), { wrapper });
        expect(result.current.contrastClass).toBeDefined();
    });
});
