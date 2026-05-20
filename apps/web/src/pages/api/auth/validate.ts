import type { NextApiRequest, NextApiResponse } from 'next';
import { resolveBackendOrigin } from '../../../config/backendOrigin';

const BACKEND_URL = resolveBackendOrigin();

const INTERNAL_PROXY_API_KEY =
  (process.env.INTERNAL_PROXY_API_KEY ||
    process.env.BACKEND_API_KEY ||
    process.env.INTERNAL_API_SECRET ||
    '').trim();

interface ForwardResponse {
  status: number;
  body: unknown;
  correlationId?: string;
}

async function safeJson<T = unknown>(res: Response): Promise<T | null> {
  try {
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
}

const getRequestHeader = (
  req: NextApiRequest,
  name: string,
): string | undefined => {
  const raw = req.headers[name.toLowerCase()];
  if (Array.isArray(raw)) return raw.join(', ');
  if (typeof raw === 'string' && raw.trim()) return raw.trim();
  return undefined;
};

async function forwardValidate(req: NextApiRequest): Promise<ForwardResponse> {
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    const authorization = getRequestHeader(req, 'authorization');
    if (authorization) {
      headers.Authorization = authorization;
    }

    if (INTERNAL_PROXY_API_KEY) {
      headers['X-Internal-API-Key'] = INTERNAL_PROXY_API_KEY;
    }

    const response = await fetchWithTimeout(
      `${BACKEND_URL}/auth/validate`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify(req.body ?? {}),
      },
      8000,
    );

    const body = (await safeJson(response)) ?? {
      detail: 'Backend returned a non-JSON response',
    };

    return {
      status: response.status,
      body,
      correlationId: response.headers.get('x-correlation-id') || undefined,
    };
  } catch {
    return {
      status: 502,
      body: { error: 'Backend unreachable' },
    };
  }
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ detail: 'Method not allowed' });
  }

  const result = await forwardValidate(req);
  if (result.correlationId) {
    res.setHeader('X-Correlation-ID', result.correlationId);
  }
  return res.status(result.status).json(result.body ?? {});
}
