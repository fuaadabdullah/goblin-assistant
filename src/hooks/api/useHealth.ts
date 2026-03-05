// Stub implementation for useHealth hook

export function useRoutingHealth() {
  return {
    settings: {
      status: 'healthy',
      timestamp: new Date().toISOString(),
    },
    isLoading: false,
    error: null,
  };
}

export function useHealth() {
  return {
    settings: {
      status: 'healthy',
      timestamp: new Date().toISOString(),
    },
    isLoading: false,
    error: null,
  };
}
