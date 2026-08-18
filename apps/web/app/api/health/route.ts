import { NextResponse } from 'next/server';
import { buildVersionedPath } from '@goblin/shared';
import { resolveBackendOrigin } from '@/config/backendOrigin';

const BACKEND_URL = resolveBackendOrigin();

type HealthStatusBody = {
  overall?: string;
  status?: string;
  timestamp?: string;
  services?: Record<string, unknown>;
  components?: Record<string, unknown>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isHealthStatusBody(value: unknown): value is HealthStatusBody {
  if (!isRecord(value)) return false;

  const overall = value['overall'];
  const status = value['status'];
  const timestamp = value['timestamp'];
  const services = value['services'];
  const components = value['components'];

  const hasStatusField = typeof overall === 'string' || typeof status === 'string';
  const validTimestamp = timestamp === undefined || typeof timestamp === 'string';
  const validServices = services === undefined || isRecord(services);
  const validComponents = components === undefined || isRecord(components);

  return hasStatusField && validTimestamp && validServices && validComponents;
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

function fallbackHealth(reason: string) {
  return {
    overall: 'degraded',
    timestamp: new Date().toISOString(),
    services: {},
    proxy: {
      status: 'backend_unavailable',
      reason,
    },
  };
}

const DEGRADED_HEADERS = {
  'Cache-Control': 'no-store',
  'Retry-After': '5',
};

export async function GET() {
  try {
    const response = await fetchWithTimeout(`${BACKEND_URL}${buildVersionedPath('health')}`, 5000);
    const body = await safeJson(response);

    if (response.ok && isHealthStatusBody(body)) {
      return NextResponse.json(body, {
        status: 200,
        headers: { 'Cache-Control': 'no-store' },
      });
    }

    return NextResponse.json(fallbackHealth(`backend_status_${response.status}`), {
      status: 503,
      headers: DEGRADED_HEADERS,
    });
  } catch (error) {
    const reason =
      error instanceof Error && error.name === 'AbortError'
        ? 'backend_timeout'
        : 'backend_unreachable';
    return NextResponse.json(fallbackHealth(reason), {
      status: 503,
      headers: DEGRADED_HEADERS,
    });
  }
}
