// lib/services/search-service.ts
import { apiClient } from './api-client';
import type { SearchRequest, SearchResult } from '../types';

export class SearchService {
  // Perform semantic search
  async search(request: SearchRequest): Promise<SearchResult[]> {
    const response = await apiClient.post<{ results: SearchResult[] }>('/search', request);

    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Search failed');
    }

    return response.data.results;
  }

  // Index document for search
  async indexDocument(
    content: string,
    metadata?: {
      source?: string;
      title?: string;
      tags?: string[];
      category?: string;
    }
  ): Promise<{ id: string; indexed: boolean }> {
    const response = await apiClient.post<{ id: string; indexed: boolean }>('/search/index', {
      content,
      metadata,
    });

    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to index document');
    }

    return response.data;
  }

  // Delete indexed document
  async deleteDocument(documentId: string): Promise<void> {
    const response = await apiClient.delete(`/search/index/${documentId}`);

    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to delete document');
    }
  }

  // Get search statistics
  async getStats(): Promise<{
    totalDocuments: number;
    totalChunks: number;
    lastIndexed?: Date;
    indexSize?: number;
  }> {
    const response = await apiClient.get<{
      totalDocuments: number;
      totalChunks: number;
      lastIndexed?: string;
      indexSize?: number;
    }>('/search/stats');

    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to get search stats');
    }

    return {
      ...response.data,
      lastIndexed: response.data.lastIndexed ? new Date(response.data.lastIndexed) : undefined,
    };
  }

  // Rebuild search index
  async rebuildIndex(): Promise<{ success: boolean; duration: number }> {
    const response = await apiClient.post<{ success: boolean; duration: number }>('/search/rebuild');

    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to rebuild index');
    }

    return response.data;
  }

  // Get similar documents
  async findSimilar(documentId: string, limit = 5): Promise<SearchResult[]> {
    const response = await apiClient.get<{ results: SearchResult[] }>(
      `/search/similar/${documentId}?limit=${limit}`
    );

    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to find similar documents');
    }

    return response.data.results;
  }
}

// Export singleton instance
export const searchService = new SearchService();