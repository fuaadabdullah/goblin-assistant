// app/components/dashboard/CostTracking.tsx
'use client';

import React, { useEffect, useState } from 'react';
import { formatCurrency } from '../../lib/utils';

interface CostData {
  totalCost: number;
  monthlyBudget: number;
  budgetUsed: number;
  costsByProvider: Array<{
    provider: string;
    cost: number;
    percentage: number;
  }>;
  costsByDay: Array<{
    date: string;
    cost: number;
  }>;
  averageCostPerRequest: number;
  costTrend: string;
  projectedMonthlyCost: number;
}

export const CostTracking: React.FC = () => {
  const [costData, setCostData] = useState<CostData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCostData = async () => {
      try {
        const response = await fetch('/api/analytics/costs');
        if (!response.ok) {
          throw new Error('Failed to fetch cost data');
        }
        const data = await response.json();
        setCostData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchCostData();
  }, []);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            <div className="h-4 bg-gray-200 rounded w-2/3"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !costData) {
    return (
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="text-center text-red-600">
          <p className="text-lg font-medium">Failed to load cost tracking data</p>
          <p className="text-sm text-gray-500 mt-1">
            {error || 'Unable to fetch data'}
          </p>
        </div>
      </div>
    );
  }

  const averageCostPerRequest = costData.averageCostPerRequest;

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">Cost Tracking</h2>
        <div className="text-sm text-gray-500">
          Last updated: {new Date().toLocaleDateString()}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-blue-50 p-4 rounded-lg">
          <div className="text-sm font-medium text-blue-600 mb-1">Total Cost</div>
          <div className="text-2xl font-bold text-blue-900">
            {formatCurrency(costData.totalCost)}
          </div>
        </div>

        <div className="bg-green-50 p-4 rounded-lg">
          <div className="text-sm font-medium text-green-600 mb-1">Budget Used</div>
          <div className="text-2xl font-bold text-green-900">
            {costData.budgetUsed.toFixed(1)}%
          </div>
        </div>

        <div className="bg-purple-50 p-4 rounded-lg">
          <div className="text-sm font-medium text-purple-600 mb-1">Avg Cost/Request</div>
          <div className="text-2xl font-bold text-purple-900">
            {formatCurrency(averageCostPerRequest)}
          </div>
        </div>
      </div>

      {/* Provider Cost Breakdown */}
      <div className="mb-6">
        <h3 className="text-lg font-medium text-gray-900 mb-3">Cost by Provider</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Provider
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cost
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Percentage
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {costData.costsByProvider.map((provider) => (
                <tr key={provider.provider}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {provider.provider}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatCurrency(provider.cost)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {provider.percentage.toFixed(1)}%
                  </td>
                </tr>
              ))}
              {costData.costsByProvider.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-6 py-4 text-center text-sm text-gray-500">
                    No cost data available
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Daily Usage */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-3">Daily Costs</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cost
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {costData.costsByDay
                .sort((a, b) => b.date.localeCompare(a.date))
                .slice(0, 7)
                .map((day) => (
                  <tr key={day.date}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {new Date(day.date).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatCurrency(day.cost)}
                    </td>
                  </tr>
                ))}
              {costData.costsByDay.length === 0 && (
                <tr>
                  <td colSpan={2} className="px-6 py-4 text-center text-sm text-gray-500">
                    No daily data available
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
