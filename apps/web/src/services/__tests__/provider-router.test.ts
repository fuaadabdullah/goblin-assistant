import { beforeEach, describe, expect, it, vi } from 'vitest';

type ProviderRouterModule = typeof import('../provider-router');

const STORAGE_KEY = 'goblin-provider-router-metrics';

async function loadProviderRouter(): Promise<ProviderRouterModule> {
  vi.resetModules();
  return import('../provider-router');
}

describe('provider-router', () => {
  beforeEach(() => {
    // Re-register passthrough doMock to cancel any lingering doMock override
    vi.doMock('../../../../../config/providers.json', async (importOriginal) => {
      return importOriginal();
    });
    vi.resetModules();
    window.sessionStorage.clear();
  });

  describe('metrics persistence', () => {
    it('hydrates metrics from sessionStorage on module load', async () => {
      window.sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          openai: {
            latencies: [150, 200],
            succ: 3,
            fail: 1,
            updatedAt: 123,
          },
        })
      );

      const providerRouter = await loadProviderRouter();

      expect(providerRouter.__getMetricsSnapshotForTests()).toEqual({
        openai: {
          latencies: [150, 200],
          succ: 3,
          fail: 1,
          updatedAt: 123,
        },
      });
    });

    it('ignores malformed persisted payloads', async () => {
      window.sessionStorage.setItem(STORAGE_KEY, '{bad-json');

      const providerRouter = await loadProviderRouter();

      expect(providerRouter.__getMetricsSnapshotForTests()).toEqual({});
    });

    it('ignores invalid-shape persisted payloads', async () => {
      window.sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          openai: {
            latencies: ['bad'],
            succ: 1,
            fail: 0,
            updatedAt: 123,
          },
        })
      );

      const providerRouter = await loadProviderRouter();

      expect(providerRouter.__getMetricsSnapshotForTests()).toEqual({});
    });

    it('persists updates after backend telemetry arrives', async () => {
      const providerRouter = await loadProviderRouter();

      providerRouter.updateMetricsFromBackend('openai', 140, true);

      const stored = JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) || '{}');
      expect(stored.openai.latencies).toEqual([140]);
      expect(stored.openai.succ).toBe(1);
      expect(stored.openai.fail).toBe(0);
      expect(typeof stored.openai.updatedAt).toBe('number');
    });

    it('trims persisted latency samples to the latest 100', async () => {
      const providerRouter = await loadProviderRouter();

      for (let i = 1; i <= 105; i += 1) {
        providerRouter.updateMetricsFromBackend('openai', i, true);
      }

      const metrics = providerRouter.__getMetricsSnapshotForTests().openai;
      expect(metrics.latencies).toHaveLength(100);
      expect(metrics.latencies[0]).toBe(6);
      expect(metrics.latencies[99]).toBe(105);
    });

    it('tracks success and failure independently', async () => {
      const providerRouter = await loadProviderRouter();

      providerRouter.updateMetricsFromBackend('openai', 100, true);
      providerRouter.updateMetricsFromBackend('openai', 150, false);

      expect(providerRouter.__getMetricsSnapshotForTests().openai).toMatchObject({
        succ: 1,
        fail: 1,
        latencies: [100, 150],
      });
    });

    it('surfaces schema_version mismatches as a validation error', async () => {
      vi.doMock('../../../../../config/providers.json', () => ({
        __esModule: true,
        default: {
          schema_version: 99,
          version: 2,
          default_timeout_ms: 12000,
          providers: {},
        },
      }));

      const providerRouter = await loadProviderRouter();

      expect(providerRouter.getProviderRouterConfigError()).toBeTruthy();
      expect(providerRouter.getProviderRouterConfigError()?.message).toContain(
        'expected schema_version=1'
      );
    });

    it('keeps metrics isolated per provider', async () => {
      const providerRouter = await loadProviderRouter();

      providerRouter.updateMetricsFromBackend('openai', 100, true);
      providerRouter.updateMetricsFromBackend('anthropic', 200, false);

      expect(providerRouter.__getMetricsSnapshotForTests()).toMatchObject({
        openai: { latencies: [100], succ: 1, fail: 0 },
        anthropic: { latencies: [200], succ: 0, fail: 1 },
      });
    });

    it('falls back to in-memory behavior when sessionStorage is unavailable', async () => {
      const providerRouter = await loadProviderRouter();
      const originalSessionStorage = window.sessionStorage;

      try {
        Object.defineProperty(window, 'sessionStorage', {
          configurable: true,
          get() {
            throw new Error('blocked');
          },
        });
        providerRouter.updateMetricsFromBackend('openai', 120, true);

        expect(providerRouter.__getMetricsSnapshotForTests().openai).toMatchObject({
          latencies: [120],
          succ: 1,
          fail: 0,
        });
      } finally {
        Object.defineProperty(window, 'sessionStorage', {
          configurable: true,
          value: originalSessionStorage,
        });
      }
    });
  });

  describe('topProvidersFor', () => {
    it('returns providers for a supported capability', async () => {
      const providerRouter = await loadProviderRouter();

      const providers = providerRouter.topProvidersFor('chat');

      expect(Array.isArray(providers)).toBe(true);
      expect(providers.length).toBeGreaterThan(0);
    });

    it('limits results to the requested count', async () => {
      const providerRouter = await loadProviderRouter();

      const providers = providerRouter.topProvidersFor('chat', false, false, 3);

      expect(providers.length).toBeLessThanOrEqual(3);
    });

    it('returns an empty array for unsupported capabilities', async () => {
      const providerRouter = await loadProviderRouter();

      expect(providerRouter.topProvidersFor('nonexistent-capability')).toEqual([]);
    });

    it('changes ranking when poor latency metrics are applied to the current leader', async () => {
      const providerRouter = await loadProviderRouter();

      const before = providerRouter.topProvidersFor('chat', false, false, 5);
      expect(before[0]).toBe('groq');

      for (let i = 0; i < 8; i += 1) {
        providerRouter.updateMetricsFromBackend('groq', 100_000, false);
      }

      const after = providerRouter.topProvidersFor('chat', false, false, 5);
      expect(after[0]).not.toBe('groq');
    });
  });

  describe('getRuntimeClient', () => {
    it('returns the runtime client object', async () => {
      const providerRouter = await loadProviderRouter();

      expect(providerRouter.getRuntimeClient()).toBeDefined();
      expect(typeof providerRouter.getRuntimeClient()).toBe('object');
    });
  });
});
