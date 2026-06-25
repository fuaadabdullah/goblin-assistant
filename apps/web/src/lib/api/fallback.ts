export const hasMockFallbackSignal = (value: string | undefined): boolean =>
  typeof value === 'string' &&
  (value.includes('no-configured-providers') ||
    value.includes('provider-access-denied') ||
    value.includes('Backend unreachable'));

