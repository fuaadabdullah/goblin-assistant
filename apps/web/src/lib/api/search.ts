import { getBackend, postBackend } from './shared';

export const searchMethods = {
  async getSearchCollections() {
    return getBackend('/search/collections');
  },

  async searchQuery(collection: string, query: string, limit = 8) {
    return postBackend('/search/query', { collection, query, limit });
  },
};
