"use client";

import { useState, useEffect } from 'react';
import { RefreshCw, Database, Trash2, BarChart3 } from 'lucide-react';

interface CacheEntry {
  key: string;
  value: string;
  size: string;
  lastAccessed: string;
  hitCount: number;
  ttl?: number;
}

export default function CachePage() {
  const [cacheData, setCacheData] = useState<CacheEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    totalEntries: 0,
    totalSize: '0 MB',
    hitRate: 0,
    memoryUsage: 0
  });

  // Mock data for demonstration
  const mockCacheData: CacheEntry[] = [
    {
      key: 'user_session_123',
      value: 'encrypted_session_data',
      size: '2.3 KB',
      lastAccessed: '2025-01-15 11:30:00',
      hitCount: 45,
      ttl: 3600
    },
    {
      key: 'provider_config_openai',
      value: 'openai_configuration',
      size: '1.8 KB',
      lastAccessed: '2025-01-15 11:25:00',
      hitCount: 23,
      ttl: 7200
    },
    {
      key: 'chat_history_456',
      value: 'chat_conversation_data',
      size: '15.7 KB',
      lastAccessed: '2025-01-15 11:20:00',
      hitCount: 12,
      ttl: 1800
    }
  ];

  const mockStats = {
    totalEntries: 1247,
    totalSize: '45.6 MB',
    hitRate: 87.3,
    memoryUsage: 67
  };

  const fetchCacheData = async () => {
    setLoading(true);
    try {
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      setCacheData(mockCacheData);
      setStats(mockStats);
    } catch (error) {
      console.error('Failed to fetch cache data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCacheData();
  }, []);

  const clearCache = async (key?: string) => {
    if (key) {
      setCacheData(prev => prev.filter(entry => entry.key !== key));
    } else {
      setCacheData([]);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg border p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Cache Management</h1>
            <p className="text-sm text-gray-600 mt-1">
              Monitor and manage Redis cache operations
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => clearCache()}
              className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              <Trash2 className="h-4 w-4" />
              <span>Clear All</span>
            </button>
            <button
              onClick={fetchCacheData}
              disabled={loading}
              className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <div className="flex items-center">
            <Database className="h-8 w-8 text-blue-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Total Entries</p>
              <p className="text-2xl font-bold text-gray-900">{stats.totalEntries.toLocaleString()}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <div className="flex items-center">
            <BarChart3 className="h-8 w-8 text-green-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Cache Size</p>
              <p className="text-2xl font-bold text-gray-900">{stats.totalSize}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <div className="flex items-center">
            <RefreshCw className="h-8 w-8 text-purple-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Hit Rate</p>
              <p className="text-2xl font-bold text-gray-900">{stats.hitRate}%</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg border p-4 shadow-sm">
          <div className="flex items-center">
            <Database className="h-8 w-8 text-orange-500" />
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-600">Memory Usage</p>
              <p className="text-2xl font-bold text-gray-900">{stats.memoryUsage}%</p>
            </div>
          </div>
        </div>
      </div>

      {/* Cache Entries */}
      <div className="bg-white rounded-lg border shadow-sm">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Cache Entries</h2>
        </div>
        <div className="p-6">
          <div className="space-y-4">
            {cacheData.map((entry, index) => (
              <div key={index} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="text-sm font-medium text-gray-900 font-mono">{entry.key}</h3>
                      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">{entry.size}</span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600">
                      <div>
                        <span className="font-medium">Last Accessed:</span>
                        <br />
                        {entry.lastAccessed}
                      </div>
                      <div>
                        <span className="font-medium">Hit Count:</span>
                        <br />
                        {entry.hitCount}
                      </div>
                      <div>
                        <span className="font-medium">TTL:</span>
                        <br />
                        {entry.ttl ? `${entry.ttl}s` : 'No expiry'}
                      </div>
                      <div>
                        <span className="font-medium">Value Type:</span>
                        <br />
                        {typeof entry.value}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => clearCache(entry.key)}
                      className="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
                    >
                      Clear
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          {cacheData.length === 0 && !loading && (
            <div className="text-center py-8">
              <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">No cache entries found</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
