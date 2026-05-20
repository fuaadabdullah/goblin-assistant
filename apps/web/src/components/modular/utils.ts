export const formatTitle = (s: string): string => {
  return s.trim().replace(/\s+/g, ' ').replace(/[^\w\s\-]/g, '');
};

export const sampleHelper = (n: number): number => Math.max(0, Math.floor(n));
