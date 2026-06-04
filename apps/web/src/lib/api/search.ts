import { V1_API_PREFIX, getBackend, postBackend } from './shared';

export const searchMethods = {
  async getSearchCollections() {
    return getBackend(`${V1_API_PREFIX}/search/collections`);
  },

  async searchQuery(collection: string, query: string, limit = 8) {
    return postBackend(`${V1_API_PREFIX}/search/query`, { collection, query, limit });
  },
};
