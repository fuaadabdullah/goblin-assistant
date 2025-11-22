import { useState } from "react";
import { runtimeClient } from "../api/tauri-client";

interface Props {
	providers: string[];
	selectedProvider: string;
	onProviderChange?: (provider: string) => void;
}

export default function APIKeyManager({
	providers,
	selectedProvider,
	onProviderChange,
}: Props) {
	const [key, setKey] = useState<string>("");
	const [status, setStatus] = useState<string>("");

	async function handleSave() {
		if (!selectedProvider) return;
		try {
			// Persist and update runtime providers immediately
			await runtimeClient.setProviderApiKey(selectedProvider, key);
			setStatus("Saved securely");
			setKey("");
		} catch (e) {
			setStatus("Failed to save: " + e);
		}
	}

	async function handleGet() {
		if (!selectedProvider) return;
		try {
			const k = await runtimeClient.getApiKey(selectedProvider);
			setStatus(k ? "Key present" : "No key stored");
		} catch (e) {
			setStatus("Failed to read: " + e);
		}
	}

	async function handleClear() {
		if (!selectedProvider) return;
		try {
			await runtimeClient.clearApiKey(selectedProvider);
			setStatus("Cleared");
		} catch (e) {
			setStatus("Failed to clear: " + e);
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
					onChange={(e) => onProviderChange && onProviderChange(e.target.value)}
				>
					{providers.map((p) => (
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
					value={key}
					onChange={(e) => setKey(e.currentTarget.value)}
					placeholder="Enter API key"
				/>
			</div>

			<div className="btn-row">
				<button onClick={handleSave} disabled={!selectedProvider || !key}>
					Save
				</button>
				<button onClick={handleGet} disabled={!selectedProvider}>
					Check
				</button>
				<button onClick={handleClear} disabled={!selectedProvider}>
					Clear
				</button>
			</div>

			{status && <div className="status">{status}</div>}
		</div>
	);
}
