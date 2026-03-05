// app/components/dashboard/ProviderHealth.tsx
'use client';

import React, { useEffect, useState } from 'react';

interface ProviderData {
  id: string;
  name: string;
  status: string;
  latency: number;
  uptime: number;
  errorRate: number;
  totalRequests: number;
  successRate: number;
  lastError: string | null;
  models: string[];
}

interface ProviderHealthData {
  providers: ProviderData[];
  overallHealth: string;
  totalActiveProviders: number;
  averageLatency: number;
  totalErrors: number;
  lastHealthCheck: string;
}

export const ProviderHealth: React.FC = () => {
  const [providerData, setProviderData] = useState<ProviderHealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProviderData = async () => {
      try {
        const response = await fetch('/api/analytics/providers');
        if (!response.ok) {
          throw new Error('Failed to fetch provider data');
        }
        const data = await response.json();
        setProviderData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchProviderData();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
        return 'from-emerald-500/20 to-green-500/20 text-emerald-400 border-emerald-500/30';
      case 'degraded':
        return 'from-amber-500/20 to-yellow-500/20 text-amber-400 border-amber-500/30';
      case 'unhealthy':
        return 'from-red-500/20 to-pink-500/20 text-red-400 border-red-500/30';
      default:
        return 'from-slate-500/20 to-gray-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'healthy':
        return '🟢';
      case 'degraded':
        return '🟡';
      case 'unhealthy':
        return '🔴';
      default:
        return '⚪';
    }
  };

  if (loading) {
    return (
      <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm border border-white/20 rounded-xl p-8 shadow-xl">
        <div className="animate-pulse">
          <div className="h-8 bg-white/20 rounded w-1/4 mb-6"></div>
          <div className="space-y-4">
            <div className="h-4 bg-white/20 rounded w-3/4"></div>
            <div className="h-4 bg-white/20 rounded w-1/2"></div>
            <div className="h-4 bg-white/20 rounded w-2/3"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !providerData) {
    return (
      <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm border border-white/20 rounded-xl p-8 shadow-xl">
        <div className="text-center text-red-400">
          <p className="text-lg font-semibold mb-2">Failed to load provider health data</p>
          <p className="text-slate-400 text-sm">
            {error || 'Unable to fetch data'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm border border-white/20 rounded-xl p-8 shadow-xl">
      <div className="flex items-center justify-between mb-8">
        <h2 className="text-2xl font-bold text-white">Provider Health</h2>
        <div className="text-sm text-slate-400">
          Real-time status monitoring
        </div>
      </div>

      <div className="space-y-4">
        {providerData.providers.map((provider) => (
          <div key={provider.id} className="flex items-center justify-between p-6 border border-white/20 rounded-xl bg-white/5 hover:bg-white/10 transition-all duration-300 group">
            <div className="flex items-center space-x-4">
              <span className="text-2xl group-hover:scale-110 transition-transform duration-300">
                {getStatusIcon(provider.status)}
              </span>
              <div>
                <div className="font-semibold text-white text-lg">{provider.name}</div>
                <div className="text-sm text-slate-400">{provider.id}</div>
              </div>
            </div>

            <div className="flex items-center space-x-6">
              <div className="text-right">
                <div className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-gradient-to-r ${getStatusColor(provider.status)} border`}>
                  {provider.status}
                </div>
                <div className="text-sm text-slate-400 mt-2">
                  {provider.latency}ms latency
                </div>
              </div>

              <div className="text-right text-sm">
                <div className="text-white font-medium">
                  {provider.errorRate.toFixed(1)}% error rate
                </div>
                <div className="text-slate-400">
                  {provider.uptime.toFixed(1)}% uptime
                </div>
              </div>
            </div>
          </div>
        ))}

        {providerData.providers.length === 0 && (
          <div className="text-center py-8 text-slate-400">
            No providers configured
          </div>
        )}
      </div>

      {/* Summary Stats */}
      <div className="mt-8 pt-8 border-t border-white/20">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="text-center group hover:scale-105 transition-transform duration-300">
            <div className="text-3xl font-bold text-white mb-2">
              {providerData.totalActiveProviders}
            </div>
            <div className="text-sm text-slate-400">Total Providers</div>
          </div>

          <div className="text-center group hover:scale-105 transition-transform duration-300">
            <div className="text-3xl font-bold text-emerald-400 mb-2">
              {providerData.providers.filter(p => p.status === 'healthy').length}
            </div>
            <div className="text-sm text-slate-400">Healthy</div>
          </div>

          <div className="text-center group hover:scale-105 transition-transform duration-300">
            <div className="text-3xl font-bold text-amber-400 mb-2">
              {providerData.providers.filter(p => p.status === 'degraded').length}
            </div>
            <div className="text-sm text-slate-400">Degraded</div>
          </div>

          <div className="text-center group hover:scale-105 transition-transform duration-300">
            <div className="text-3xl font-bold text-red-400 mb-2">
              {providerData.providers.filter(p => p.status === 'unhealthy').length}
            </div>
            <div className="text-sm text-slate-400">Unhealthy</div>
          </div>
        </div>
      </div>
    </div>
  );
};
