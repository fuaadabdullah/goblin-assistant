// src/components/dashboard/RoutingDashboard.tsx
'use client';

import React, { useEffect, useState } from 'react';

interface CostTracking {
  hourly_budget: number;
  current_spend: number;
  remaining: number;
  hour_start: string;
  request_count: number;
  should_use_cheaper: boolean;
}

interface RoutingStatus {
  available: boolean;
  default_strategy: string;
  cost_tracking: CostTracking;
  healthy_providers: string[];
  available_providers: string[];
  best_providers: string[];
}

interface Strategy {
  id: string;
  name: string;
  description: string;
  priority_order: string[];
}

export const RoutingDashboard: React.FC = () => {
  const [routingStatus, setRoutingStatus] = useState<RoutingStatus | null>(null);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch routing status
        const statusRes = await fetch('/api/routing/status');
        const statusData = await statusRes.json();
        setRoutingStatus(statusData);

        // Fetch available strategies
        const strategiesRes = await fetch('/api/routing/strategies');
        const strategiesData = await strategiesRes.json();
        setStrategies(strategiesData.strategies || []);

      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStrategyIcon = (id: string) => {
    switch (id) {
      case 'cost_optimized': return '💰';
      case 'quality_first': return '⭐';
      case 'latency_optimized': return '⚡';
      case 'local_first': return '🏠';
      case 'balanced': return '⚖️';
      default: return '🎯';
    }
  };

  const getBudgetColor = (remaining: number, total: number) => {
    const percentage = (remaining / total) * 100;
    if (percentage > 70) return 'bg-green-500';
    if (percentage > 30) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  if (loading) {
    return (
      <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm border border-white/20 rounded-xl p-8 shadow-xl">
        <div className="animate-pulse">
          <div className="h-8 bg-white/20 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-3 gap-4">
            <div className="h-24 bg-white/20 rounded"></div>
            <div className="h-24 bg-white/20 rounded"></div>
            <div className="h-24 bg-white/20 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gradient-to-br from-red-500/10 to-red-500/5 backdrop-blur-sm border border-red-500/20 rounded-xl p-8 shadow-xl">
        <div className="text-center text-red-400">
          <p className="text-lg font-semibold mb-2">Failed to load routing data</p>
          <p className="text-slate-400 text-sm">{error}</p>
        </div>
      </div>
    );
  }

  const costTracking = routingStatus?.cost_tracking;

  return (
    <div className="space-y-6">
      {/* Main Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Active Strategy */}
        <div className="bg-gradient-to-br from-indigo-500/20 to-purple-500/20 backdrop-blur-sm border border-indigo-500/30 rounded-xl p-6 shadow-xl">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm font-medium">Active Strategy</span>
            <span className="text-2xl">{getStrategyIcon(routingStatus?.default_strategy || '')}</span>
          </div>
          <div className="text-xl font-bold text-white capitalize">
            {routingStatus?.default_strategy?.replace(/_/g, ' ') || 'Unknown'}
          </div>
          <div className="text-slate-400 text-sm mt-1">
            Routing decisions powered by AI
          </div>
        </div>

        {/* Budget Tracker */}
        <div className="bg-gradient-to-br from-emerald-500/20 to-green-500/20 backdrop-blur-sm border border-emerald-500/30 rounded-xl p-6 shadow-xl">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm font-medium">Hourly Budget</span>
            <span className="text-2xl">💵</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold text-white">
              ${costTracking?.current_spend?.toFixed(2) || '0.00'}
            </span>
            <span className="text-slate-400">
              / ${costTracking?.hourly_budget?.toFixed(2) || '10.00'}
            </span>
          </div>
          {/* Budget Progress Bar */}
          <div className="mt-3 h-2 bg-slate-700 rounded-full overflow-hidden">
            <div 
              className={`h-full ${getBudgetColor(costTracking?.remaining || 10, costTracking?.hourly_budget || 10)} transition-all duration-300`}
              style={{ 
                width: `${((costTracking?.remaining || 10) / (costTracking?.hourly_budget || 10)) * 100}%` 
              }}
            />
          </div>
          <div className="text-slate-400 text-xs mt-2">
            ${costTracking?.remaining?.toFixed(2) || '10.00'} remaining this hour
          </div>
        </div>

        {/* Provider Status */}
        <div className="bg-gradient-to-br from-cyan-500/20 to-blue-500/20 backdrop-blur-sm border border-cyan-500/30 rounded-xl p-6 shadow-xl">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-400 text-sm font-medium">Healthy Providers</span>
            <span className="text-2xl">🟢</span>
          </div>
          <div className="text-xl font-bold text-white">
            {routingStatus?.healthy_providers?.length || 0} / {routingStatus?.available_providers?.length || 0}
          </div>
          <div className="text-slate-400 text-sm mt-1">
            {routingStatus?.cost_tracking?.request_count || costTracking?.request_count || 0} requests this hour
          </div>
        </div>
      </div>

      {/* Strategies Grid */}
      <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm border border-white/20 rounded-xl p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span>🎯</span> Available Routing Strategies
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {strategies.map((strategy) => (
            <div 
              key={strategy.id}
              className={`p-4 rounded-lg border transition-all duration-200 ${
                routingStatus?.default_strategy === strategy.id
                  ? 'bg-indigo-500/20 border-indigo-500/50 ring-2 ring-indigo-500/30'
                  : 'bg-white/5 border-white/10 hover:bg-white/10'
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">{getStrategyIcon(strategy.id)}</span>
                <span className="font-medium text-white">{strategy.name}</span>
              </div>
              <p className="text-slate-400 text-sm">{strategy.description}</p>
              {routingStatus?.default_strategy === strategy.id && (
                <div className="mt-2 inline-flex items-center px-2 py-1 rounded-full bg-indigo-500/30 text-indigo-300 text-xs">
                  Active
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Provider Priority List */}
      {routingStatus?.best_providers && routingStatus.best_providers.length > 0 && (
        <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm border border-white/20 rounded-xl p-6 shadow-xl">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <span>🏆</span> Provider Priority (Best to Fallback)
          </h3>
          <div className="flex flex-wrap gap-2">
            {routingStatus.best_providers.map((provider, index) => {
              const isHealthy = routingStatus.healthy_providers?.includes(provider);
              return (
                <div
                  key={provider}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${
                    isHealthy 
                      ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-300'
                      : 'bg-amber-500/20 border-amber-500/30 text-amber-300'
                  }`}
                >
                  <span className="text-xs font-bold text-slate-500">#{index + 1}</span>
                  <span className="font-medium">{provider.replace(/_/g, ' ')}</span>
                  <span>{isHealthy ? '✓' : '!'}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default RoutingDashboard;
