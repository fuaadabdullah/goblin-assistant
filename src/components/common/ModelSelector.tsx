import React, { useEffect, useState } from 'react';
import { runtimeClient } from '@/api/api-client';
import type { ProviderModelOption } from '@/types/api';
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
  const [models, setModels] = useState<ProviderModelOption[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let isMounted = true;
    if (provider) {
      setLoading(true);
      const loadModels = async () => {
        try {
          const modelOptions = await runtimeClient.getProviderModelOptions(provider);
          if (!isMounted) return;
          setModels(modelOptions);
        } catch (error) {
          console.error(error);
          if (!isMounted) return;
          setModels([]);
        } finally {
          if (isMounted) {
            setLoading(false);
          }
        }
      };
      loadModels();
    } else {
      setModels([]);
      setLoading(false);
    }

    return () => {
      isMounted = false;
    };
  }, [provider]);

  if (!provider) {
    return (
      <div className="text-sm text-muted" data-testid="model-selector-placeholder">
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
              key={model.name}
              value={model.name}
              disabled={!model.isSelectable}
              data-testid={`model-option-${model.name.replace(/[^a-zA-Z0-9]/g, '-')}`}
            >
              {model.name}
              {!model.isSelectable && model.healthReason
                ? ` (Unavailable: ${model.healthReason})`
                : ''}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {loading && (
        <p className="text-sm text-muted" data-testid="model-loading">
          Loading models...
        </p>
      )}
    </div>
  );
};

export default ModelSelector;
