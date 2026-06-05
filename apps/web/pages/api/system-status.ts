import type { NextApiRequest, NextApiResponse } from 'next';
import { resolveBackendOrigin } from '@/config/backendOrigin';

const BACKEND_URL = resolveBackendOrigin();

type ServiceState = 'ok' | 'degraded' | 'down' | 'unknown';

interface SystemStatus {
  models: ServiceState;
  routing: ServiceState;
  sandbox: ServiceState;
  updatedAt: string;
}

async function fetchWithTimeout(url: string, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

async function safeJson<T = unknown>(res: Response): Promise<T | null> {
  try {
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

function mapStatus(raw: string | undefined): ServiceState {
  if (!raw) return 'unknown';
  const s = raw.toLowerCase();
  if (s === 'healthy' || s === 'ok') return 'ok';
  if (s === 'degraded' || s === 'warning') return 'degraded';
  if (s === 'unhealthy' || s === 'down' || s === 'error') return 'down';
  return 'unknown';
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const fallback: SystemStatus = {
    models: 'unknown',
    routing: 'unknown',
    sandbox: 'unknown',
    updatedAt: new Date().toISOString(),
  };

  try {
    const [healthRes, sandboxRes] = await Promise.allSettled([
      fetchWithTimeout(`${BACKEND_URL}/api/v1/health`, 5000),
      fetchWithTimeout(`${BACKEND_URL}/api/v1/health/sandbox/status`, 5000),
    ]);

    // Parse main health response
    let models: ServiceState = 'unknown';
    let routing: ServiceState = 'unknown';
    if (healthRes.status === 'fulfilled' && healthRes.value.ok) {
      const body = await safeJson<{
        data?: {
          components?: {
            providers?: { status?: string };
            routing?: { status?: string };
          };
        };
      }>(healthRes.value);
      models = mapStatus(body?.data?.components?.providers?.status);
      routing = mapStatus(body?.data?.components?.routing?.status);
    }

    // Parse sandbox health response
    let sandbox: ServiceState = 'unknown';
    if (sandboxRes.status === 'fulfilled' && sandboxRes.value.ok) {
      const body = await safeJson<{ status?: string }>(sandboxRes.value);
      sandbox = mapStatus(body?.status);
    }

    return res.status(200).json({ models, routing, sandbox, updatedAt: new Date().toISOString() });
  } catch {
    return res.status(200).json(fallback);
  }
}
