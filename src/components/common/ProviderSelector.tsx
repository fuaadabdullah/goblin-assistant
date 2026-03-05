import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface Props {
  providers?: string[];
  selected?: string;
  onChange?: (provider: string) => void;
}

export default function ProviderSelector({ providers, selected, onChange }: Props) {
  if (!providers || providers.length === 0) return null;

  return (
    <div className="provider-selector" data-testid="provider-selector">
      <label htmlFor="provider-select" data-testid="provider-label">
        Provider:
      </label>
      <Select
        value={selected || providers[0]}
        onValueChange={(value: string) => onChange && onChange(value)}
      >
        <SelectTrigger
          id="provider-select"
          aria-label="Select provider"
          data-testid="provider-select"
        >
          <SelectValue placeholder="Select provider" />
        </SelectTrigger>
        <SelectContent>
          {providers.map(p => (
            <SelectItem key={p} value={p} data-testid={`provider-option-${p}`}>
              {p}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
