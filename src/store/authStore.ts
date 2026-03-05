// Stub implementation for authStore

export function useAuthStore() {
  return {
    user: null,
    isAuthenticated: false,
    isLoading: false,
    login: async () => {},
    logout: async () => {},
  };
}
