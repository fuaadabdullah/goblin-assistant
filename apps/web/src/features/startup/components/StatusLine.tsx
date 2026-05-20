interface StatusLineProps {
  label: string;
  state: 'complete' | 'active' | 'pending' | 'error';
}

const statusStyles: Record<StatusLineProps['state'], string> = {
  complete: 'text-success',
  active: 'text-primary',
  pending: 'text-muted',
  error: 'text-danger',
};

const StatusLine = ({ label, state }: StatusLineProps) => (
  <div className="flex items-center gap-3">
    <span
      className={`flex h-2.5 w-2.5 rounded-full ${
        state === 'complete'
          ? 'bg-success'
          : state === 'active'
            ? 'bg-primary animate-pulse'
            : state === 'error'
              ? 'bg-danger'
              : 'bg-border'
      }`}
    />
    <span className={`text-sm font-medium ${statusStyles[state]}`}>{label}</span>
  </div>
);

export default StatusLine;
