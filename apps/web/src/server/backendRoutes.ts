export const V1_API_PREFIX = '/api/v1' as const;

export const buildVersionedPath = (...segments: string[]): string => {
  const cleaned = segments.map((segment) => segment.trim().replace(/^\/|\/$/g, '')).filter(Boolean);
  return cleaned.length === 0 ? V1_API_PREFIX : `${V1_API_PREFIX}/${cleaned.join('/')}`;
};
