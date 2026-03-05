// components/dashboard/UsageStats.tsx
'use client';

import { useEffect, useState, useMemo } from 'react';
import { formatNumber, formatCurrency } from '../../lib/utils/index';
import { TrendingUp, MessageSquare, DollarSign, Clock } from 'lucide-react';
import { clsx } from 'clsx';

interface UsageStatsProps {
  className?: string;
}

interface UsageData {
  totalRequests: number;
  totalTokens: number;
  totalCost: number;
  averageResponseTime: number;
  requestsByDay: Array<{
    date: string;
    requests: number;
    tokens: number;
    cost: number;
  }>;
}

export function UsageStats({ className }: UsageStatsProps) {
  const [usageData, setUsageData] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUsageData = async () => {
      try {
        const response = await fetch('/api/analytics/usage');
        if (!response.ok) {
          throw new Error('Failed to fetch usage data');
        }
        const data = await response.json();
        setUsageData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchUsageData();
  }, []);

  const stats = useMemo(() => {
    if (!usageData) return null;

    // Calculate changes compared to previous period (simplified - using last 7 days vs previous 7 days)
    const currentPeriod = usageData.requestsByDay.slice(-7);
    const previousPeriod = usageData.requestsByDay.slice(-14, -7);

    const currentTotal = currentPeriod.reduce((sum, day) => sum + day.requests, 0);
    const previousTotal = previousPeriod.reduce((sum, day) => sum + day.requests, 0);

    const currentTokens = currentPeriod.reduce((sum, day) => sum + day.tokens, 0);
    const previousTokens = previousPeriod.reduce((sum, day) => sum + day.tokens, 0);

    const currentCost = currentPeriod.reduce((sum, day) => sum + day.cost, 0);
    const previousCost = previousPeriod.reduce((sum, day) => sum + day.cost, 0);

    const calculateChange = (current: number, previous: number) => {
      if (previous === 0) return current > 0 ? 100 : 0;
      return ((current - previous) / previous) * 100;
    };

    return {
      totalMessages: {
        value: usageData.totalRequests,
        change: calculateChange(currentTotal, previousTotal),
      },
      totalTokens: {
        value: usageData.totalTokens,
        change: calculateChange(currentTokens, previousTokens),
      },
      totalCost: {
        value: usageData.totalCost,
        change: calculateChange(currentCost, previousCost),
      },
      avgResponseTime: {
        value: usageData.averageResponseTime * 1000, // Convert to ms
        change: 0, // TODO: Calculate from historical data
      },
    };
  }, [usageData]);

  const StatCard = ({
    title,
    value,
    change,
    icon: Icon,
    format = (v: number) => v.toString(),
    color = 'blue'
  }: {
    title: string;
    value: number;
    change: number;
    icon: React.ComponentType<{ className?: string }>;
    format?: (value: number) => string;
    color?: 'blue' | 'green' | 'yellow' | 'red';
  }) => {
    const colorClasses = {
      blue: 'from-blue-500/20 to-cyan-500/20 text-blue-400',
      green: 'from-emerald-500/20 to-green-500/20 text-emerald-400',
      yellow: 'from-amber-500/20 to-orange-500/20 text-amber-400',
      red: 'from-red-500/20 to-pink-500/20 text-red-400',
    };

    const changeColorClasses = {
      positive: 'text-emerald-400',
      negative: 'text-red-400',
    };

    return (
      <div className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm border border-white/20 rounded-xl p-6 shadow-xl hover:from-white/15 hover:to-white/10 transition-all duration-300 group hover:-translate-y-1 hover:shadow-2xl">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-300 mb-2">{title}</p>
            <p className="text-3xl font-bold text-white">
              {format(value)}
            </p>
          </div>
          <div className={`w-16 h-16 bg-gradient-to-br ${colorClasses[color]} rounded-xl flex items-center justify-center group-hover:scale-110 transition-all duration-300 shadow-lg shadow-emerald-500/10`}>
            <Icon className="w-8 h-8 text-white" />
          </div>
        </div>

        {change !== 0 && (
          <div className="flex items-center mt-4 pt-4 border-t border-white/20">
            <TrendingUp
              className={clsx(
                'w-5 h-5 mr-2',
                change > 0 ? changeColorClasses.positive : changeColorClasses.negative
              )}
            />
            <span
              className={clsx(
                'text-sm font-semibold',
                change > 0 ? changeColorClasses.positive : changeColorClasses.negative
              )}
            >
              {change > 0 ? '+' : ''}{change.toFixed(1)}%
            </span>
            <span className="text-sm text-slate-400 ml-2">vs last period</span>
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className={clsx('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8', className)}>
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm border border-white/20 rounded-xl p-6 shadow-xl animate-pulse">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="h-4 bg-white/20 rounded w-24 mb-4"></div>
                <div className="h-10 bg-white/20 rounded w-20"></div>
              </div>
              <div className="w-16 h-16 bg-white/20 rounded-xl"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className={clsx('bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm border border-white/20 rounded-xl p-8 shadow-xl', className)}>
        <div className="text-center text-red-400">
          <p className="text-lg font-semibold mb-2">Failed to load usage statistics</p>
          <p className="text-slate-400 text-sm">
            {error || 'Unable to fetch data'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={clsx('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8', className)}>
      <StatCard
        title="Total Messages"
        value={stats.totalMessages.value}
        change={stats.totalMessages.change}
        icon={MessageSquare}
        format={formatNumber}
        color="blue"
      />

      <StatCard
        title="Total Tokens"
        value={stats.totalTokens.value}
        change={stats.totalTokens.change}
        icon={TrendingUp}
        format={formatNumber}
        color="green"
      />

      <StatCard
        title="Total Cost"
        value={stats.totalCost.value}
        change={stats.totalCost.change}
        icon={DollarSign}
        format={(v) => formatCurrency(v, 'USD')}
        color="yellow"
      />

      <StatCard
        title="Avg Response Time"
        value={stats.avgResponseTime.value}
        change={stats.avgResponseTime.change}
        icon={Clock}
        format={(v) => `${v.toFixed(1)}ms`}
        color="red"
      />
    </div>
  );
}
