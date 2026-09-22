export const providerKeys = {
  get(provider: string): string | null {
    void provider;
    return null;
  },

  set(provider: string, key: string): void {
    void provider;
    void key;
  },

  remove(provider: string): void {
    void provider;
  },
};
