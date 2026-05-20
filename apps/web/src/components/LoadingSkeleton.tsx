import Card from './Card';

const createPlaceholderKeys = (prefix: string, count: number) =>
  Array.from({ length: count }, (_, index) => `${prefix}-${index + 1}`);

const STATUS_CARD_PLACEHOLDER_KEYS = createPlaceholderKeys('status-card-placeholder', 3);
const DASHBOARD_STATUS_CARD_KEYS = createPlaceholderKeys('dashboard-status-card', 6);
const DASHBOARD_ACTION_KEYS = createPlaceholderKeys('dashboard-action', 4);

/**
 * Loading skeleton for status cards
 */
export function StatusCardSkeleton() {
  return (
    <Card className="border-2 border-border animate-pulse" role="status" aria-label="Loading card">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {/* Icon skeleton */}
          <div className="w-8 h-8 bg-surface-hover rounded" />
          <div>
            {/* Title skeleton */}
            <div className="h-4 w-24 bg-surface-hover rounded mb-2" />
            {/* Status chip skeleton */}
            <div className="h-5 w-16 bg-surface-hover rounded-full" />
          </div>
        </div>
      </div>

      {/* Meta grid skeleton */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-4">
        {STATUS_CARD_PLACEHOLDER_KEYS.map((placeholderKey) => (
          <div
            key={placeholderKey}
            className="bg-surface-hover rounded-lg p-3 border border-border min-h-[64px]"
          >
            <div className="h-3 w-16 bg-surface-active rounded mb-2" />
            <div className="h-4 w-12 bg-surface-active rounded" />
          </div>
        ))}
      </div>
      <span className="sr-only">Loading content...</span>
    </Card>
  );
}

/**
 * Loading skeleton for stat cards
 */
export function StatCardSkeleton() {
  return (
    <Card
      padded
      bordered
      radius="md"
      className="min-h-[64px] animate-pulse"
      role="status"
      aria-label="Loading statistic"
    >
      <div className="flex items-center justify-between">
        <div className="h-3 w-16 bg-surface-hover rounded" />
        <div className="h-6 w-20 bg-surface-hover rounded" />
      </div>
      <span className="sr-only">Loading statistic...</span>
    </Card>
  );
}

/**
 * List item skeleton for loading states
 */
export function ListItemSkeleton() {
  return (
    <div
      className="bg-surface rounded-lg shadow-sm border border-border p-4 animate-pulse"
      role="status"
      aria-label="Loading list item"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="h-6 w-20 bg-surface-hover rounded-full" />
          <div className="h-6 w-24 bg-surface-hover rounded-full" />
        </div>
        <div className="h-4 w-16 bg-surface-hover rounded" />
      </div>
      <div className="h-4 w-full bg-surface-hover rounded mb-2" />
      <div className="h-4 w-3/4 bg-surface-hover rounded" />
      <span className="sr-only">Loading item...</span>
    </div>
  );
}

/**
 * List loading skeleton
 */
export function ListSkeleton({ count = 5 }: { count?: number }) {
  const placeholderKeys = createPlaceholderKeys('list-item-placeholder', count);

  return (
    <div className="space-y-3" role="status" aria-label={`Loading ${count} items`}>
      {placeholderKeys.map((placeholderKey) => (
        <ListItemSkeleton key={placeholderKey} />
      ))}
      <span className="sr-only">Loading list...</span>
    </div>
  );
}

/**
 * Provider card skeleton for loading states
 */
export function ProviderCardSkeleton() {
  return (
    <div
      className="bg-surface rounded-lg border border-border p-4 animate-pulse"
      role="status"
      aria-label="Loading provider"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-surface-hover rounded" />
          <div>
            <div className="h-5 w-32 bg-surface-hover rounded mb-2" />
            <div className="h-3 w-20 bg-surface-hover rounded" />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-6 w-16 bg-surface-hover rounded-full" />
          <div className="h-6 w-6 bg-surface-hover rounded" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="h-4 w-full bg-surface-hover rounded" />
        <div className="h-4 w-full bg-surface-hover rounded" />
      </div>
      <span className="sr-only">Loading provider...</span>
    </div>
  );
}

/**
 * Dashboard loading state with skeleton grid
 */
export function DashboardSkeleton() {
  return (
    <div
      className="min-h-screen bg-bg py-6 px-4"
      role="status"
      aria-live="polite"
      aria-label="Loading dashboard"
    >
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header skeleton */}
        <div className="flex items-center justify-between">
          <div>
            <div className="h-8 w-64 bg-surface-hover rounded mb-2 animate-pulse" />
            <div className="h-4 w-48 bg-surface-hover rounded animate-pulse" />
          </div>
          <div className="flex items-center gap-3">
            <div className="h-10 w-24 bg-surface-hover rounded animate-pulse" />
            <div className="h-10 w-36 bg-surface-hover rounded animate-pulse" />
          </div>
        </div>

        {/* Cost banner skeleton */}
        <div className="bg-surface rounded-xl p-4 border border-border animate-pulse">
          <div className="h-5 w-32 bg-surface-hover rounded mb-3" />
          <div className="grid-auto-fit gap-4">
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </div>
        </div>

        {/* Health cards grid skeleton */}
        <div className="grid-auto-fit gap-4 auto-rows-fr">
          {DASHBOARD_STATUS_CARD_KEYS.map((placeholderKey) => (
            <StatusCardSkeleton key={placeholderKey} />
          ))}
        </div>

        {/* Quick actions skeleton */}
        <div className="bg-surface rounded-xl border border-border p-6 animate-pulse">
          <div className="h-6 w-32 bg-surface-hover rounded mb-4" />
          <div className="grid-auto-fit gap-3">
            {DASHBOARD_ACTION_KEYS.map((placeholderKey) => (
              <div key={placeholderKey} className="h-12 bg-surface-hover rounded-lg" />
            ))}
          </div>
        </div>
      </div>
      <span className="sr-only">Loading dashboard data...</span>
    </div>
  );
}
