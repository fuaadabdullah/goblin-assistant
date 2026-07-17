import { renderHook, act } from '@testing-library/react';

const { runtimeFlagState, getRuntimeFlagMock, getExperimentVariantMock } = vi.hoisted(() => {
  const runtimeFlagState = { current: true };
  return {
    runtimeFlagState,
    getRuntimeFlagMock: vi.fn(() => runtimeFlagState.current),
    getExperimentVariantMock: vi.fn((experiment: { name: string }, userId: string) =>
      `${experiment.name}:${userId}`
    ),
  };
});

vi.mock('../../config/features', () => ({
  featureFlags: {
    ragEnabled: false,
    multiProvider: false,
    passkeyAuth: false,
    googleAuth: false,
    sandbox: false,
    search: false,
    admin: false,
    debugMode: false,
  },
  getRuntimeFlag: getRuntimeFlagMock,
  getExperimentVariant: getExperimentVariantMock,
}));

import { useExperiment } from '../useExperiment';
import { useFeatureFlag } from '../useFeatureFlag';

describe('feature hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    runtimeFlagState.current = true;
  });

  it('subscribes to runtime flag changes', () => {
    const { result } = renderHook(() => useFeatureFlag('ragEnabled'));

    expect(result.current).toBe(true);
    expect(getRuntimeFlagMock).toHaveBeenCalledWith('ragEnabled');

    act(() => {
      runtimeFlagState.current = false;
      window.dispatchEvent(new Event('storage'));
    });

    expect(result.current).toBe(false);
  });

  it('returns the chosen experiment variant for a user', () => {
    const experiment = {
      name: 'chat-composer-v2',
      variants: ['control', 'treatment'] as const,
    };

    const { result, rerender } = renderHook(
      ({ userId }) => useExperiment(experiment, userId),
      {
        initialProps: { userId: 'user-1' },
      }
    );

    expect(result.current).toBe('chat-composer-v2:user-1');
    expect(getExperimentVariantMock).toHaveBeenCalledWith(experiment, 'user-1');

    rerender({ userId: 'user-2' });
    expect(result.current).toBe('chat-composer-v2:user-2');
    expect(getExperimentVariantMock).toHaveBeenCalledWith(experiment, 'user-2');
  });
});
