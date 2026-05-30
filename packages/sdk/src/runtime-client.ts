export type GoblinClientRequest = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  headers?: Record<string, string>;
  body?: unknown;
  signal?: AbortSignal;
};

export type GoblinClient = {
  request<TResponse>(path: string, request?: GoblinClientRequest): Promise<TResponse>;
};

export function createGoblinClient(baseUrl: string): GoblinClient {
  const normalizedBaseUrl = baseUrl.replace(/\/+$/, "");

  return {
    async request<TResponse>(path: string, request: GoblinClientRequest = {}): Promise<TResponse> {
      const response = await fetch(`${normalizedBaseUrl}${path}`, {
        method: request.method ?? "GET",
        headers: {
          "Content-Type": "application/json",
          ...request.headers,
        },
        body: request.body === undefined ? undefined : JSON.stringify(request.body),
        signal: request.signal,
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(`Goblin SDK request failed: ${response.status} ${response.statusText} ${text}`);
      }

      return (await response.json()) as TResponse;
    },
  };
}
