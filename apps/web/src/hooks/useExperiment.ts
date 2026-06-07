'use client';

import { useMemo } from 'react';
import { getExperimentVariant, type Experiment, type ExperimentVariant } from '../config/features';

/**
 * Returns the stable experiment variant for the current user.
 *
 * The returned variant is deterministic across sessions for the same userId +
 * experiment name, so users are never re-bucketed unintentionally.
 *
 * Usage:
 *   const variant = useExperiment(
 *     { name: 'chat-composer-v2', variants: ['control', 'treatment'] },
 *     userId,
 *   );
 *   if (variant === 'treatment') { ... }
 */
export function useExperiment(experiment: Experiment, userId: string): ExperimentVariant {
  return useMemo(
    () => getExperimentVariant(experiment, userId),
    // experiment object is expected to be stable (defined outside the component)
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [experiment.name, userId],
  );
}
