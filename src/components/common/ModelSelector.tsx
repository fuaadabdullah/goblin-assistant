import React, { useEffect, useState } from 'react';
import { runtimeClient } from '@/api/api-client';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface Props {
  provider?: string;
  selected?: string;
  onChange: (model: string) => void;
}

const ModelSelector: React.FC<Props> = ({ provider, selected, onChange }) => {
  const [models, setModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (provider) {
      setLoading(true);
      runtimeClient
        .getProviderModels(provider)
        .then(setModels)
        .catch(console.error)
        .finally(() => setLoading(false));
    } else {
      setModels([]);
    }
  }, [provider]);

  if (!provider) {
    return (
      <div className="text-sm text-muted-foreground" data-testid="model-selector-placeholder">
        Select a provider first
      </div>
    );
  }

  return (
    <div className="space-y-2" data-testid="model-selector">
      <label htmlFor="model-select" className="text-sm font-medium" data-testid="model-label">
        Model:
      </label>
      <Select value={selected || ''} onValueChange={onChange} disabled={loading}>
        <SelectTrigger data-testid="model-select" aria-label="Select a model">
          <SelectValue placeholder="Select a model..." />
        </SelectTrigger>
        <SelectContent>
          {(models || []).map(model => (
            <SelectItem
              key={model}
              value={model}
              data-testid={`model-option-${model.replace(/[^a-zA-Z0-9]/g, '-')}`}
            >
              {model}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {loading && (
        <p className="text-sm text-muted-foreground" data-testid="model-loading">
          Loading models...
        </p>
      )}
    </div>
  );
};

export default ModelSelector;
