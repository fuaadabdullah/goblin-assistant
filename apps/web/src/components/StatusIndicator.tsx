import React from 'react';

type Status = 'ok' | 'degraded' | 'down' | 'unknown';

const colorFor = (s: Status) => {
  switch (s) {
    case 'ok':
      return 'bg-emerald-500';
    case 'degraded':
      return 'bg-amber-500';
    case 'down':
      return 'bg-red-500';
    default:
      return 'bg-gray-400';
  }
};

export default function StatusIndicator(props: Readonly<{
  label: string;
  status: Status;
  size?: 'sm' | 'md';
}>) {
  const { label, status, size = 'md' } = props;
  const dotSize = size === 'sm' ? 'w-2 h-2' : 'w-3 h-3';

  return (
    <div className="flex items-center gap-2">
      <span
        aria-hidden="true"
        className={`inline-block ${dotSize} rounded-full ${colorFor(status)} inline-flex shrink-0`}
      />
      <span className="text-sm text-text">{label}</span>
      <span className="sr-only">{`${label}: ${status}`}</span>
    </div>
  );
}
