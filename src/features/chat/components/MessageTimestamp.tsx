'use client';

interface MessageTimestampProps {
  createdAt: string;
  showRelative?: boolean;
}

const MessageTimestamp = ({ createdAt, showRelative = true }: MessageTimestampProps) => {
  const date = new Date(createdAt);

  const formatTime = (d: Date): string => {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true });
  };

  const formatFullDate = (d: Date): string => {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const isToday = d.toDateString() === today.toDateString();
    const isYesterday = d.toDateString() === yesterday.toDateString();

    if (isToday) {
      return `Today at ${formatTime(d)}`;
    }
    if (isYesterday) {
      return `Yesterday at ${formatTime(d)}`;
    }

    return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) +
      ` at ${formatTime(d)}`;
  };

  const displayText = showRelative ? formatFullDate(date) : formatTime(date);

  return (
    <time
      dateTime={date.toISOString()}
      className="inline-block text-xs text-muted leading-none"
      title={date.toLocaleString()}
    >
      {displayText}
    </time>
  );
};

export default MessageTimestamp;
