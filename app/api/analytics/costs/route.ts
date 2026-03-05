// app/api/analytics/costs/route.ts
import { NextResponse } from 'next/server';
import { db } from '../../../lib/services/database';

export async function GET() {
  try {
    // Get cost data from the last 7 days
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 7);

    const costLogs = await db.getCostStats(undefined, startDate, endDate);

    if (!costLogs) {
      // Return mock data if database is not available
      const mockCostData = {
        totalCost: 45.67,
        monthlyBudget: 100.0,
        budgetUsed: 45.7,
        costsByProvider: [
          { provider: 'openai', cost: 28.45, percentage: 62.3 },
          { provider: 'anthropic', cost: 12.34, percentage: 27.0 },
          { provider: 'google', cost: 4.88, percentage: 10.7 },
        ],
        costsByDay: [
          { date: '2024-01-01', cost: 2.34 },
          { date: '2024-01-02', cost: 2.89 },
          { date: '2024-01-03', cost: 1.87 },
          { date: '2024-01-04', cost: 3.21 },
          { date: '2024-01-05', cost: 2.67 },
          { date: '2024-01-06', cost: 3.01 },
          { date: '2024-01-07', cost: 2.76 },
        ],
        averageCostPerRequest: 0.003,
        costTrend: 'decreasing',
        projectedMonthlyCost: 52.30,
      };

      return NextResponse.json(mockCostData);
    }

    // Aggregate the data
    const totalCost = costLogs.reduce((sum, log) => sum + (log.amount || 0), 0);
    const monthlyBudget = 100.0; // TODO: Get from user settings
    const budgetUsed = monthlyBudget > 0 ? (totalCost / monthlyBudget) * 100 : 0;

    // Group by provider
    const providerCosts = costLogs.reduce((acc, log) => {
      const provider = log.provider || 'unknown';
      if (!acc[provider]) {
        acc[provider] = 0;
      }
      acc[provider] += (log.amount || 0);
      return acc;
    }, {} as Record<string, number>);

    const costsByProvider = Object.entries(providerCosts).map(([provider, cost]) => ({
      provider,
      cost: cost as number,
      percentage: totalCost > 0 ? ((cost as number) / totalCost) * 100 : 0,
    }));

    // Group by day
    const costsByDay = costLogs.reduce((acc, log) => {
      const date = new Date(log.created_at).toISOString().split('T')[0];
      const existing = acc.find((item: { date: string; cost: number }) => item.date === date);
      if (existing) {
        existing.cost += (log.amount || 0);
      } else {
        acc.push({
          date,
          cost: log.amount || 0,
        });
      }
      return acc;
    }, [] as Array<{ date: string; cost: number }>);

    // Calculate average cost per request (simplified)
    const averageCostPerRequest = costLogs.length > 0 ? totalCost / costLogs.length : 0;

    // Calculate cost trend (simplified - compare first half vs second half)
    const midPoint = Math.floor(costsByDay.length / 2);
    const firstHalf = costsByDay.slice(0, midPoint);
    const secondHalf = costsByDay.slice(midPoint);

    const firstHalfAvg = firstHalf.length > 0
      ? firstHalf.reduce((sum: number, day: { date: string; cost: number }) => sum + day.cost, 0) / firstHalf.length
      : 0;
    const secondHalfAvg = secondHalf.length > 0
      ? secondHalf.reduce((sum: number, day: { date: string; cost: number }) => sum + day.cost, 0) / secondHalf.length
      : 0;

    let costTrend: 'increasing' | 'decreasing' | 'stable' = 'stable';
    if (secondHalfAvg > firstHalfAvg * 1.1) {
      costTrend = 'increasing';
    } else if (secondHalfAvg < firstHalfAvg * 0.9) {
      costTrend = 'decreasing';
    }

    // Project monthly cost (simple extrapolation)
    const dailyAverage = costsByDay.length > 0
      ? totalCost / costsByDay.length
      : 0;
    const projectedMonthlyCost = dailyAverage * 30;

    const costData = {
      totalCost,
      monthlyBudget,
      budgetUsed,
      costsByProvider,
      costsByDay,
      averageCostPerRequest,
      costTrend,
      projectedMonthlyCost,
    };

    return NextResponse.json(costData);

  } catch (error) {
    console.error('Analytics costs error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
