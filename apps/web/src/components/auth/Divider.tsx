interface DividerProps {
  text?: string;
}

export default function Divider({ text = 'Or' }: DividerProps) {
  return (
    <div className="relative my-6">
      <div className="absolute inset-0 flex items-center">
        <div className="w-full border-t border-border"></div>
      </div>
      <div className="relative flex justify-center text-sm">
        <span className="px-4 bg-surface text-muted font-medium">{text}</span>
      </div>
    </div>
  );
}
