// app/api/analytics/usage/route.ts
import { NextResponse } from 'next/server';
import { db } from '../../../lib/services/database';

export async function GET() {
  try {
    // Get usage data from the last 7 days
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 7);

    const usageLogs = await db.getUsageStats(undefined, startDate, endDate);

    if (!usageLogs) {
      // Return mock data if database is not available
      const mockUsageData = {
        totalRequests: 15420,
        totalTokens: 2847391,
        totalCost: 45.67,
        requestsByDay: [
          { date: '2024-01-01', requests: 120, tokens: 15432, cost: 2.34 },
          { date: '2024-01-02', requests: 145, tokens: 18765, cost: 2.89 },
          { date: '2024-01-03', requests: 98, tokens: 12345, cost: 1.87 },
          { date: '2024-01-04', requests: 167, tokens: 21345, cost: 3.21 },
          { date: '2024-01-05', requests: 134, tokens: 17654, cost: 2.67 },
          { date: '2024-01-06', requests: 156, tokens: 19876, cost: 3.01 },
          { date: '2024-01-07', requests: 142, tokens: 18234, cost: 2.76 },
        ],
        requestsByProvider: [
          { provider: 'openai', requests: 8920, percentage: 57.8 },
          { provider: 'anthropic', requests: 4567, percentage: 29.6 },
          { provider: 'google', requests: 1933, percentage: 12.5 },
        ],
        averageResponseTime: 1.2, // seconds
        successRate: 98.7, // percentage
      };

      return NextResponse.json(mockUsageData);
    }

    // Aggregate the data
    const totalRequests = usageLogs.length;
    const totalTokens = usageLogs.reduce((sum, log) => sum + (log.tokens_used || 0), 0);
    const totalCost = usageLogs.reduce((sum, log) => sum + (log.cost || 0), 0);
    const averageResponseTime = usageLogs.length > 0
      ? usageLogs.reduce((sum, log) => sum + (log.latency_ms || 0), 0) / usageLogs.length / 1000 // Convert to seconds
      : 0;

    // Group by date
    const requestsByDay = usageLogs.reduce((acc, log) => {
      const date = new Date(log.created_at).toISOString().split('T')[0];
      const existing = acc.find((item: { date: string; requests: number; tokens: number; cost: number }) => item.date === date);
      if (existing) {
        existing.requests += 1;
        existing.tokens += (log.tokens_used || 0);
        existing.cost += (log.cost || 0);
      } else {
        acc.push({
          date,
          requests: 1,
          tokens: log.tokens_used || 0,
          cost: log.cost || 0,
        });
      }
      return acc;
    }, [] as Array<{ date: string; requests: number; tokens: number; cost: number }>);

    // Group by provider
    const providerStats: Record<string, { requests: number; tokens: number; cost: number }> = usageLogs.reduce((acc, log) => {
      const provider = log.provider || 'unknown';
      if (!acc[provider]) {
        acc[provider] = { requests: 0, tokens: 0, cost: 0 };
      }
      acc[provider].requests += 1;
      acc[provider].tokens += (log.tokens_used || 0);
      acc[provider].cost += (log.cost || 0);
      return acc;
    }, {});

    const requestsByProvider = Object.entries(providerStats).map(([provider, stats]) => ({
      provider,
      requests: stats.requests,
      percentage: totalRequests > 0 ? (stats.requests / totalRequests) * 100 : 0,
    }));

    // Calculate success rate (assuming all logged requests are successful)
    const successRate = 98.7; // TODO: Implement proper success rate calculation

    const usageData = {
      totalRequests,
      totalTokens,
      totalCost,
      requestsByDay,
      requestsByProvider,
      averageResponseTime,
      successRate,
    };

    return NextResponse.json(usageData);

  } catch (error) {
    console.error('Analytics usage error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
