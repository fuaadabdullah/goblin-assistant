import { Button } from '../../../../components/ui';

export default function ProviderPromptTest({
  prompt,
  onPromptChange,
  onTest,
  isTesting,
  disabled,
}: {
  prompt: string;
  onPromptChange: (value: string) => void;
  onTest: () => void;
  isTesting: boolean;
  disabled?: boolean;
}) {
  return (
    <div className="bg-surface rounded-xl shadow-sm border border-border p-6">
      <h3 className="text-lg font-semibold text-text mb-4">Test with Custom Prompt</h3>
      <div className="space-y-4">
        <div>
          <label htmlFor="test-prompt" className="block text-sm font-medium text-text mb-2">
            Enter your test prompt:
          </label>
          <textarea
            id="test-prompt"
            value={prompt}
            onChange={e => onPromptChange(e.target.value)}
            rows={4}
            className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary bg-bg text-text"
            placeholder="e.g., Write a hello world program in Python"
          />
        </div>
        <Button
          onClick={onTest}
          disabled={disabled || !prompt.trim()}
          variant="success"
          fullWidth
        >
          {isTesting ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin" aria-hidden="true">
                🔄
              </span>
              Testing with prompt...
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              <span aria-hidden="true">🧪</span>
              Test API with Prompt
            </span>
          )}
        </Button>
      </div>
    </div>
  );
}

