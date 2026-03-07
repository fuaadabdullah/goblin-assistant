import { env } from '../config/env';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

interface HttpResponse<T> {
  data: T;
}

const buildUrl = (path: string): string => {
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  if (path.startsWith('/')) return `${env.apiBaseUrl}${path}`;
  return `${env.apiBaseUrl}/${path}`;
};

const request = async <T>(method: HttpMethod, path: string, body?: unknown): Promise<HttpResponse<T>> => {
  const response = await fetch(buildUrl(path), {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string; error?: string };
      detail = payload.detail || payload.error || detail;
    } catch {
      // keep default error message
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return { data: undefined as T };
  }

  const data = (await response.json()) as T;
  return { data };
};

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T = unknown>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T = unknown>(path: string, body?: unknown) => request<T>('PUT', path, body),
  patch: <T = unknown>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  delete: <T = unknown>(path: string) => request<T>('DELETE', path),
};
