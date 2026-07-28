import type { NextApiRequest, NextApiResponse } from 'next';
import { resolveBackendOrigin } from '../../config/backendOrigin';

const BACKEND_URL = resolveBackendOrigin();

type ServiceState = 'ok' | 'degraded' | 'down' | 'unknown';

interface SystemStatusResponse {
  models: ServiceState;
  routing: ServiceState;
  sandbox: ServiceState;
  updatedAt?: string;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<SystemStatusResponse>
) {
  if (req.method !== 'GET') {
    res.status(405).end();
    return;
  }

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    const response = await fetch(`${BACKEND_URL}/health`, {
      signal: controller.signal,
    }).finally(() => clearTimeout(timeout));

    if (!response.ok) {
      res.status(200).json({ models: 'unknown', routing: 'unknown', sandbox: 'unknown' });
      return;
    }

    const data = (await response.json()) as {
      status?: string;
      components?: {
        providers?: { status?: string };
        routing?: { status?: string };
        sandbox?: { status?: string };
      };
    };

    const map = (s?: string): ServiceState => {
      if (!s) return 'unknown';
      const l = s.toLowerCase();
      if (l === 'healthy' || l === 'ok') return 'ok';
      if (l === 'degraded' || l === 'warnings') return 'degraded';
      if (l === 'unhealthy') return 'down';
      return 'unknown';
    };

    res.status(200).json({
      models: map(data.components?.providers?.status ?? data.status),
      routing: map(data.components?.routing?.status),
      sandbox: map(data.components?.sandbox?.status),
      updatedAt: new Date().toISOString(),
    });
  } catch {
    res.status(200).json({ models: 'unknown', routing: 'unknown', sandbox: 'unknown' });
  }
}
