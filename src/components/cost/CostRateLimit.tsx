import type { RateLimitInfo } from '../../hooks/useCostEstimation';

interface Props {
  rateLimitInfo: RateLimitInfo | null;
}

export const CostRateLimit = ({ rateLimitInfo }: Props) => {
  if (!rateLimitInfo) return null;

  return (
    <div className="rate-limit">
      <span>Rate limit:</span>
      <strong>
        {rateLimitInfo.remaining}/{rateLimitInfo.limit}
      </strong>
      {rateLimitInfo.resetSeconds !== undefined && (
        <span> · resets in {rateLimitInfo.resetSeconds}s</span>
      )}
    </div>
  );
};
