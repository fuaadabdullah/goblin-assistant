import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import GoblinDemo from "./components/GoblinDemo";
import ProviderSelector from "./components/ProviderSelector";
// import ModelSelector from "./components/ModelSelector";
import CostPanel from "./components/CostPanel";
import { runtimeClient, runtimeClientDemo } from "./api/tauri-client";
import "./App.css";
import React, { useEffect, useState } from "react";

const ModelSelector: React.FC<{ provider?: string; selected?: string; onChange: (model: string) => void }> = ({ provider, selected, onChange }) => {
	console.log('ModelSelector rendering with provider:', provider);
	return React.createElement('div', { id: 'model-select' }, `Model Selector: ${provider || 'no provider'}`);
};

const qc = new QueryClient();

function App() {
	const [providers, setProviders] = useState<string[]>([]);
	const [selectedProvider, setSelectedProvider] = useState<string | undefined>(undefined);
	const [selectedModel, setSelectedModel] = useState<string | undefined>(undefined);
	const [costSummary, setCostSummary] = useState<any | null>(null);
	const [demoMode, setDemoMode] = useState<boolean>(() => {
		// Check URL parameters for demo mode override (useful for testing)
		const urlParams = new URLSearchParams(window.location.search);
		const demoParam = urlParams.get('demo');
		if (demoParam === 'false') return false;
		if (demoParam === 'true') return true;
		// Default to demo mode for interviews
		return true;
	});

	useEffect(() => {
		(async () => {
			try {
				const client = demoMode ? runtimeClientDemo : runtimeClient;
				console.log('Using client for providers:', client.constructor.name, 'demoMode:', demoMode);
				const p = await client.getProviders();
				console.log('Providers loaded:', p);
				setProviders(p);
				setSelectedProvider((prev: string | undefined) => prev ?? p[0]);
			} catch (error) {
				console.error('Error loading providers:', error);
			}
		})();
	}, [demoMode]);

	useEffect(() => {
		(async () => {
			try {
				const client = demoMode ? runtimeClientDemo : runtimeClient;
				const cs = await client.getCostSummary();
				setCostSummary(cs || { total_cost: 0, cost_by_provider: {}, cost_by_model: {} });
			} catch (_) { /* ignore */ }
		})();
	}, [selectedProvider, demoMode]);

	// Listen for task-stream events globally so the top-level cost summary
	// updates immediately when tasks emit cost deltas.
	useEffect(() => {
		let unlistenPromise: any;
		(async () => {
			const client = demoMode ? runtimeClientDemo : runtimeClient;
			unlistenPromise = await client.onTaskStream((payload: any) => {
				if (!payload) return;
				const provider = payload.provider || payload.provider_name || null;
				const delta = payload.cost_delta || payload.costDelta || 0;

				if (!provider || !delta) return;

				setCostSummary((prev: any) => {
					const cs = prev ? { ...prev } : { total_cost: 0, cost_by_provider: {}, cost_by_model: {} };
					cs.total_cost = (cs.total_cost || 0) + delta;
					cs.cost_by_provider = { ...(cs.cost_by_provider || {}) };
					cs.cost_by_provider[provider] = (cs.cost_by_provider[provider] || 0) + delta;
					return cs;
				});
			});
		})();

		return () => {
			if (unlistenPromise && typeof unlistenPromise === 'function') {
				try { unlistenPromise(); } catch (e) {}
			}
		};
	}, []);

	console.log('App component rendering, demoMode:', demoMode);
	return (
			<QueryClientProvider client={qc}>
				<div className="app-container" data-testid="app-container">
					<header className="app-header" data-testid="app-header">
						<h1 className="app-title" data-testid="app-title">Goblin Assistant — Demo</h1>
						<div className="demo-mode-toggle" data-testid="demo-mode-toggle">
							<label>
								<input
									type="checkbox"
									checked={demoMode}
									onChange={(e) => {
										console.log('Demo mode checkbox changed to:', e.target.checked);
										setDemoMode(e.target.checked);
									}}
									data-testid="demo-mode-checkbox"
								/>
								Demo Mode (Deterministic)
							</label>
						</div>
					</header>
					<div className="top-controls" data-testid="top-controls">
						<ModelSelector provider={selectedProvider} selected={selectedModel} onChange={setSelectedModel} />
						<ProviderSelector providers={providers} selected={selectedProvider} onChange={(p) => {
							setSelectedProvider(p);
							setSelectedModel(undefined); // Reset model when provider changes
						}} />
						{/* <CostPanel costSummary={costSummary} /> */}
					</div>
					<main className="app-content" data-testid="app-content">
						<GoblinDemo provider={selectedProvider} model={selectedModel} demoMode={demoMode} />
					</main>
				</div>
			</QueryClientProvider>
	);
}

export default App;
