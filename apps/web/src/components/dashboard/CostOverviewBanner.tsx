'use client';

import type { DashboardData } from '../../hooks/useDashboardData';
import { formatCost } from '@/utils/format-cost';

interface CostOverviewBannerProps {
  cost?: DashboardData['cost'];
  totalCost?: number;
  todayCost?: number;
  thisMonthCost?: number;
  byProvider?: Record<string, number>;
}

export const CostOverviewBanner = ({
  cost,
  totalCost,
  todayCost,
  thisMonthCost,
  byProvider,
}: CostOverviewBannerProps) => {
  const normalizedCost =
    cost ?? {
      total: totalCost ?? 0,
      today: todayCost ?? 0,
      thisMonth: thisMonthCost ?? 0,
      byProvider: byProvider ?? {},
    };
  const providerEntries = Object.entries(normalizedCost.byProvider);

  return (
    <section className="rounded-2xl border border-border bg-surface/80 p-4">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-widest text-muted">Usage Overview</h2>
        <p className="text-sm text-muted">
          administrators can review spend, daily usage, and provider distribution at a glance.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-widest text-muted">
            Total cost
          </div>
          <div className="mt-1 text-lg font-semibold text-text">
            {formatCost(normalizedCost.total)}
          </div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-widest text-muted">
            Today
          </div>
          <div className="mt-1 text-lg font-semibold text-text">
            {formatCost(normalizedCost.today)}
          </div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-widest text-muted">
            This month
          </div>
          <div className="mt-1 text-lg font-semibold text-text">
            {formatCost(normalizedCost.thisMonth)}
          </div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-widest text-muted">
            Providers
          </div>
          <div className="mt-1 text-lg font-semibold text-text">
            {providerEntries.length.toLocaleString()}
          </div>
        </div>
      </div>
      {providerEntries.length > 0 ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {providerEntries.map(([provider, value]) => (
            <span
              key={provider}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-bg px-3 py-1 text-xs text-muted"
            >
              <span className="font-medium text-text">{provider}</span>
              <span>{formatCost(value)}</span>
            </span>
          ))}
        </div>
      ) : null}
    </section>
  );
};

export default CostOverviewBanner;
