import { getFrontend, postFrontend } from './shared';

const INTERNAL_SEARCH_PREFIX = '/api/search';

export const searchMethods = {
  async getSearchCollections() {
    return getFrontend(`${INTERNAL_SEARCH_PREFIX}/collections`);
  },

  async searchQuery(collection: string, query: string, limit = 8) {
    return postFrontend(`${INTERNAL_SEARCH_PREFIX}/query`, { collection, query, limit });
  },
};
