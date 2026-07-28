import React from 'react';
import { Check } from 'lucide-react';
import {
  Button,
  Card,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui';
import type { ProviderDisplay } from './types';

interface ModelPreferencesSectionProps {
  providers: ProviderDisplay[];
  selectedProvider: string;
  selectedModel: string;
  selectedProviderModels: string[];
  isSaving: boolean;
  onProviderChange: (value: string) => void;
  onModelChange: (value: string) => void;
  onSave: () => Promise<void>;
}

export const ModelPreferencesSection: React.FC<ModelPreferencesSectionProps> = ({
  providers,
  selectedProvider,
  selectedModel,
  selectedProviderModels,
  isSaving,
  onProviderChange,
  onModelChange,
  onSave,
}) => (
  <Card variant="default" padding="md" className="mt-12 shadow-sm">
    <h2 className="text-xl font-semibold text-text mb-4">Model Preferences</h2>
    <p className="text-muted mb-4">Configure default model settings and routing preferences.</p>
    <div className="grid gap-4 md:grid-cols-2">
      <div>
        <label htmlFor="default-provider" className="block text-sm font-medium text-text mb-2">
          Default Provider
        </label>
        <Select value={selectedProvider} onValueChange={onProviderChange}>
          <SelectTrigger id="default-provider" className="w-full">
            <SelectValue placeholder={providers.length === 0 ? 'auto' : undefined} />
          </SelectTrigger>
          <SelectContent>
            {providers.length === 0 && <SelectItem value="auto">auto</SelectItem>}
            {providers.map((p) => (
              <SelectItem key={p.name} value={p.name}>
                {p.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div>
        <label htmlFor="default-model" className="block text-sm font-medium text-text mb-2">
          Default Model
        </label>
        <Select value={selectedModel} onValueChange={onModelChange}>
          <SelectTrigger id="default-model" className="w-full">
            <SelectValue placeholder="auto" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="auto">auto</SelectItem>
            {selectedProviderModels.map((model) => (
              <SelectItem key={model} value={model}>
                {model}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
    <div className="mt-6 flex items-center gap-3">
      <Button
        type="button"
        onClick={onSave}
        disabled={providers.length === 0}
        loading={isSaving}
        icon={!isSaving ? <Check className="w-4 h-4" /> : undefined}
      >
        {isSaving ? 'Saving...' : 'Save preferences'}
      </Button>
    </div>
  </Card>
);
