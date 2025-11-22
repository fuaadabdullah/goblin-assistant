import React, { useEffect, useState } from "react";
import { runtimeClient } from "../api/tauri-client";

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
			runtimeClient.getProviderModels(provider)
				.then(setModels)
				.catch(console.error)
				.finally(() => setLoading(false));
		} else {
			setModels([]);
		}
	}, [provider]);

	if (!provider) {
		return <div id="model-select" data-testid="model-selector-placeholder">Select a provider first</div>;
	}

	return (
		<div className="model-selector" data-testid="model-selector">
			<label htmlFor="model-select" data-testid="model-label">Model:</label>
			<select
				id="model-select"
				value={selected || ""}
				onChange={(e) => onChange(e.target.value)}
				disabled={loading}
				data-testid="model-select"
			>
				<option value="" data-testid="model-option-default">Select a model...</option>
				{(models || []).map((model) => (
					<option key={model} value={model} data-testid={`model-option-${model.replace(/[^a-zA-Z0-9]/g, '-')}`}>
						{model}
					</option>
				))}
			</select>
			{loading && <span data-testid="model-loading">Loading models...</span>}
		</div>
	);
};

export default ModelSelector;
