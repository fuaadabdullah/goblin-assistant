import { useState } from 'react';
import { runtimeClient } from '@/api/api-client';

interface Props {
  providers: string[];
  selectedProvider: string;
  onProviderChange?: (provider: string) => void;
}

export default function APIKeyManager({ providers, selectedProvider, onProviderChange }: Props) {
  const [key, setKey] = useState<string>('');
  const [status, setStatus] = useState<string>('');

  const formatError = (error: unknown) => (error instanceof Error ? error.message : String(error));

  async function handleSave() {
    if (!selectedProvider) return;
    try {
      // Persist and update runtime providers immediately
      await runtimeClient.setProviderApiKey(selectedProvider, key);
      setStatus('Saved securely');
      setKey('');
    } catch (e) {
      setStatus('Failed to save: ' + formatError(e));
    }
  }

  async function handleGet() {
    if (!selectedProvider) return;
    try {
      const k = await runtimeClient.getApiKey(selectedProvider);
      setStatus(k ? 'Key present' : 'No key stored');
    } catch (e) {
      setStatus('Failed to read: ' + formatError(e));
    }
  }

  async function handleClear() {
    if (!selectedProvider) return;
    try {
      await runtimeClient.clearApiKey(selectedProvider);
      setStatus('Cleared');
    } catch (e) {
      setStatus('Failed to clear: ' + formatError(e));
    }
  }

  return (
    <div className="api-key-manager">
      <h4>API Keys (secure)</h4>
      <div className="row">
        <label htmlFor="apikey-provider-select">Provider</label>
        <select
          id="apikey-provider-select"
          value={selectedProvider}
          onChange={e => onProviderChange && onProviderChange(e.target.value)}
        >
          {providers.map(p => (
            <option value={p} key={p}>
              {p}
            </option>
          ))}
        </select>
      </div>

      <div className="row">
        <label htmlFor="apikey-input">Key</label>
        <input
          id="apikey-input"
          type="password"
          value={key}
          onChange={e => setKey(e.currentTarget.value)}
          placeholder="Enter API key"
          autoComplete="off"
          spellCheck={false}
          aria-describedby="apikey-input-help"
        />
        <p id="apikey-input-help">Stored securely. Leave blank to keep existing key.</p>
      </div>

      <div className="btn-row">
        <button type="button" onClick={handleSave} disabled={!selectedProvider || !key}>
          Save
        </button>
        <button type="button" onClick={handleGet} disabled={!selectedProvider}>
          Check
        </button>
        <button type="button" onClick={handleClear} disabled={!selectedProvider}>
          Clear
        </button>
      </div>

      {status && (
        <div className="status" role="status" aria-live="polite" aria-atomic="true">
          {status}
        </div>
      )}
    </div>
  );
}
