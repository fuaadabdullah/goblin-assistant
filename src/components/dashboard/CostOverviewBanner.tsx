interface Props {
  totalCost: number;
  todayCost: number;
  thisMonthCost: number;
  byProvider: Record<string, number>;
}

export const CostOverviewBanner = ({ totalCost, todayCost, thisMonthCost, byProvider }: Props) => {
  const providers = Object.entries(byProvider);

  return (
    <div className="bg-surface rounded-xl border border-border p-6">
      <h2 className="text-lg font-semibold text-text">Usage Overview</h2>
      <p className="text-sm text-muted mb-4">
        For administrators: estimated usage costs across the system.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div>
          <div className="text-sm text-muted">Total cost</div>
          <div className="text-xl font-semibold">${totalCost.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-sm text-muted">Today</div>
          <div className="text-xl font-semibold">${todayCost.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-sm text-muted">This month</div>
          <div className="text-xl font-semibold">${thisMonthCost.toFixed(2)}</div>
        </div>
      </div>

      {providers.length > 0 && (
        <div className="mt-4 text-sm text-muted">
          {providers.map(([provider, value]) => (
            <span key={provider} className="mr-3">
              {provider}: ${value.toFixed(2)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};
