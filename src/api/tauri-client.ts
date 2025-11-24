import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

// FastAPI backend URL (when using the FastAPI runtime)
const FASTAPI_BASE = import.meta.env.VITE_FASTAPI_URL || "http://127.0.0.1:8000";
const RUNTIME: string = (import.meta.env.VITE_GOBLIN_RUNTIME as string) || "fastapi";
const MOCK_API: boolean = import.meta.env.VITE_MOCK_API === "true";

// Runtime selection: 'fastapi' for development (Vite + FastAPI), 'tauri' for production builds
// Set VITE_GOBLIN_RUNTIME in .env file or environment variables
// Mock API: returns static data for testing when backend is unavailable
// Set VITE_MOCK_API=true in .env file or environment variables

export interface GoblinStatus {
	id: string;
	name: string;
	title: string;
	status: string;
	guild?: string;
}

export interface ExecuteRequest {
	goblin: string;
	task: string;
	streaming?: boolean;
	provider?: string;
	model?: string;
	code?: string;
}

export interface GoblinResponse {
	goblin: string;
	task: string;
	reasoning: string;
	tool?: string;
	command?: string;
	output?: string;
	duration_ms: number;
	cost?: number;
	model?: string;
	provider?: string;
}

export interface MemoryEntry {
	id: string;
	goblin: string;
	task: string;
	response: string;
	timestamp: number;
	kpis?: string;
}

export interface CostSummary {
	total_cost: number;
	cost_by_provider: Record<string, number>;
	cost_by_model: Record<string, number>;
}

export interface OrchestrationStep {
	id: string;
	goblin: string;
	task: string;
	dependencies: string[];
	batch: number;
}

export interface OrchestrationPlan {
	steps: OrchestrationStep[];
	total_batches: number;
	max_parallel: number;
	estimated_cost?: number;
}

export interface StreamEvent {
	content: string;
	done: boolean;
}

export class TauriRuntimeClient {
	async getGoblins(): Promise<GoblinStatus[]> {
		return invoke("get_goblins");
	}

	async getProviders(): Promise<string[]> {
		return invoke("get_providers");
	}

	async getProviderModels(provider: string): Promise<string[]> {
		return invoke("get_provider_models", { provider });
	}

	async executeTask(
		goblin: string,
		task: string,
		streaming = false,
		code?: string,
		provider?: string,
		model?: string,
	): Promise<string> {
		return invoke("execute_task", {
			goblinId: goblin,
			task,
			streaming,
			args: { code, provider, model },
		});
	}

	async getHistory(goblin: string, limit = 10): Promise<MemoryEntry[]> {
		return invoke("get_history", { goblin, limit });
	}

	async getStats(goblin: string): Promise<any> {

		return invoke("get_stats", { goblin });
	}

	async getCostSummary(): Promise<CostSummary> {
		return invoke("get_cost_summary");
	}

	async parseOrchestration(
		text: string,
		defaultGoblin?: string,
	): Promise<OrchestrationPlan> {
		return invoke("parse_orchestration", {
			text,
			default_goblin: defaultGoblin,
		});
	}

	// Streaming execution with callback
	async executeTaskStreaming(
		goblin: string,
		task: string,
		onChunk: (chunk: any) => void,
		onComplete?: (response: any) => void,
		code?: string,
		provider?: string,
		model?: string,
	): Promise<void> {
		return new Promise<void>(async (resolve, reject) => {
			let taskId: string | null = null;

			// Listen for task-stream events
			const unlisten = await listen("task-stream", (event: { payload: any }) => {
				const payload = event.payload;

				// If we don't have taskId yet, allow first payload to set it
				if (!taskId && payload.taskId) {
					taskId = payload.taskId;
				}

				// Only process events for the active task
				if (payload.taskId && taskId && payload.taskId !== taskId) {
					return;
				}

				onChunk(payload);

				// Check if this is the final result (has 'result' field)
				if (payload.result !== undefined) {
					try {
						unlisten();
					} catch (e) {}
					if (onComplete) {
						try { onComplete(payload); } catch (e) {}
					}
					resolve();
				}
			});

			try {
				taskId = await this.executeTask(goblin, task, true, code, provider, model);
			} catch (e) {
				try { unlisten(); } catch (err) {}
				reject(e);
			}
		});
	}

	async onTaskStream(callback: (payload: any) => void) {
		return listen("task-stream", (event: { payload: any }) => {
			callback(event.payload);
		});
	}

	async storeApiKey(provider: string, key: string): Promise<void> {
		return invoke("store_api_key", { provider, key });
	}

	async getApiKey(provider: string): Promise<string | null> {
		return invoke("get_api_key", { provider });
	}

	async clearApiKey(provider: string): Promise<void> {
		return invoke("clear_api_key", { provider });
	}

	async setProviderApiKey(provider: string, key: string): Promise<void> {
		return invoke("set_provider_api_key", { provider, key });
	}
}

// runtimeClient will be dynamic based on VITE_GOBLIN_RUNTIME
// runtimeClient will be exported after the FastApiRuntimeClient class is defined.

// FastAPI-based runtime client (direct HTTP + SSE streaming)
export class FastApiRuntimeClient {
	async getGoblins(): Promise<GoblinStatus[]> { return []; }
	async getProviders(): Promise<string[]> {
		const res = await fetch(`${FASTAPI_BASE}/providers`);
		return (await res.json()) as string[];
	}
	async getProviderModels(provider: string): Promise<string[]> {
		const res = await fetch(`${FASTAPI_BASE}/models/${provider}`);
		return (await res.json()) as string[];
	}
	async executeTask(goblin: string, task: string, _streaming = false, code?: string, provider?: string, model?: string): Promise<string> {
		const res = await fetch(`${FASTAPI_BASE}/execute`, {
			method: "POST",
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ goblin, task, code, provider, model })
		});
		const body = await res.json();
		return body.taskId;
	}

	async storeApiKey(provider: string, key: string): Promise<void> {
		await fetch(`${FASTAPI_BASE}/api-keys/${provider}`, {
			method: "POST",
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(key)
		});
	}

	async getApiKey(provider: string): Promise<string | null> {
		const res = await fetch(`${FASTAPI_BASE}/api-keys/${provider}`);
		const data = await res.json();
		return data.key || null;
	}

	async clearApiKey(provider: string): Promise<void> {
		await fetch(`${FASTAPI_BASE}/api-keys/${provider}`, {
			method: "DELETE"
		});
	}
	async getHistory(_goblin: string, _limit = 10): Promise<MemoryEntry[]> { return [] }
	async getStats(_goblin: string): Promise<any> { return {}; }
	async getCostSummary(): Promise<CostSummary> {
		return { total_cost: 0, cost_by_provider: {}, cost_by_model: {} };
	}
	async parseOrchestration(text: string, defaultGoblin?: string): Promise<OrchestrationPlan> {
		const res = await fetch(`${FASTAPI_BASE}/parse`, {
			method: "POST",
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ text, default_goblin: defaultGoblin }),
		});
		return await res.json();
	}

	async executeTaskStreaming(goblin: string, task: string, onChunk: (chunk: any) => void, onComplete?: (response: any) => void, code?: string, provider?: string, model?: string): Promise<void> {
		const taskId = await this.executeTask(goblin, task, true, code, provider, model);
		// open a streaming connection to /stream endpoint
		const evtSourceUrl = `${FASTAPI_BASE}/stream?task_id=${taskId}&goblin=${encodeURIComponent(goblin)}&task=${encodeURIComponent(task)}`;
		const evtSource = new EventSource(evtSourceUrl);
		return new Promise<void>((resolve, reject) => {
			evtSource.onmessage = (e: MessageEvent) => {
				try {
					const payload = JSON.parse(e.data);
					onChunk(payload);
					if (payload.result !== undefined) {
						if (onComplete) onComplete(payload);
						evtSource.close();
						resolve();
					}
				} catch (err) {
					// ignore parse errors
				}
			};
			evtSource.onerror = (err) => { try { evtSource.close(); } catch (e) {}; reject(err); };
		});
	}

	async onTaskStream(_callback: (payload: any) => void) { /* no-op */ }
	async setProviderApiKey(_provider: string, _key: string): Promise<void> { return; }
}

// Demo runtime client for interview demonstrations - provides deterministic, pre-recorded responses
export class DemoRuntimeClient {
	// Pre-recorded responses for common orchestration templates
	private readonly demoResponses = {
		"docs-writer: document this code THEN code-writer: write a unit test": {
			"docs-writer": {
				response: `# add(a, b) Function Documentation

## Overview
A simple arithmetic function that adds two numbers together.

## Parameters
- \`a\` (number): The first number to add
- \`b\` (number): The second number to add

## Returns
- \`number\`: The sum of a and b

## Example Usage
\`\`\`javascript
const result = add(5, 3); // Returns 8
\`\`\`

## Notes
This function performs basic addition without any error checking or type validation.`,
				cost: 0.012,
				tokens: 156
			},
			"code-writer": {
				response: `# Unit Test for add() Function

\`\`\`javascript
describe('add() function', () => {
  test('adds two positive numbers correctly', () => {
    expect(add(2, 3)).toBe(5);
    expect(add(10, 15)).toBe(25);
  });

  test('adds positive and negative numbers correctly', () => {
    expect(add(5, -3)).toBe(2);
    expect(add(-2, -3)).toBe(-5);
  });

  test('adds with zero correctly', () => {
    expect(add(0, 5)).toBe(5);
    expect(add(5, 0)).toBe(5);
    expect(add(0, 0)).toBe(0);
  });

  test('handles decimal numbers', () => {
    expect(add(1.5, 2.5)).toBe(4);
    expect(add(0.1, 0.2)).toBeCloseTo(0.3);
  });
});
\`\`\``,
				cost: 0.018,
				tokens: 203
			}
		},
		"code-writer: analyze this code for issues THEN code-writer: suggest optimizations": {
			"code-writer": {
				response: `# Code Analysis: add() Function

## Issues Found
1. **No input validation**: Function doesn't check if inputs are numbers
2. **No error handling**: Will return NaN for invalid inputs like strings
3. **Limited type safety**: No TypeScript types or JSDoc annotations
4. **No edge case handling**: Doesn't handle very large numbers or special values

## Potential Runtime Issues
- \`add("5", "3")\` returns "53" (string concatenation)
- \`add(null, 5)\` returns 5 (type coercion)
- \`add(undefined, 5)\` returns NaN
- \`add(Infinity, -Infinity)\` returns NaN

## Recommendations
1. Add input type checking
2. Add JSDoc documentation
3. Consider using TypeScript for better type safety
4. Add error handling for edge cases`,
				cost: 0.015,
				tokens: 178
			},
			"code-writer-2": {
				response: `# Optimization Suggestions for add() Function

## Performance Optimizations
1. **Use strict equality**: No changes needed for simple addition
2. **Avoid unnecessary operations**: Current implementation is already optimal

## Code Quality Improvements
\`\`\`javascript
/**
 * Adds two numbers together
 * @param {number} a - First number
 * @param {number} b - Second number
 * @returns {number} Sum of a and b
 * @throws {TypeError} If inputs are not numbers
 */
function add(a, b) {
  if (typeof a !== 'number' || typeof b !== 'number') {
    throw new TypeError('Both arguments must be numbers');
  }
  if (!isFinite(a) || !isFinite(b)) {
    throw new RangeError('Arguments must be finite numbers');
  }
  return a + b;
}
\`\`\`

## Benefits of Changes
- **Type Safety**: Prevents string concatenation and type coercion
- **Error Handling**: Clear error messages for invalid inputs
- **Documentation**: JSDoc provides better IDE support
- **Edge Case Handling**: Prevents NaN results from Infinity/-Infinity

## Alternative: TypeScript Version
\`\`\`typescript
function add(a: number, b: number): number {
  return a + b;
}
\`\`\``,
				cost: 0.022,
				tokens: 245
			}
		}
	};

	async getGoblins(): Promise<GoblinStatus[]> {
		return [
			{ id: "docs-writer", name: "docs-writer", title: "Documentation Writer", status: "available" },
			{ id: "code-writer", name: "code-writer", title: "Code Writer", status: "available" }
		];
	}

	async getProviders(): Promise<string[]> {
		return ["demo"];
	}

	async getProviderModels(_provider: string): Promise<string[]> {
		return ["demo-model"];
	}

	async executeTask(
		_goblin: string,
		_task: string,
		_streaming = false,
		_code?: string,
		_provider?: string,
		_model?: string
	): Promise<string> {
		// Simulate async delay for realism
		await new Promise(resolve => setTimeout(resolve, 200));
		return `demo_task_${_goblin}_${Date.now()}`;
	}

	async getHistory(_goblin: string, _limit = 10): Promise<MemoryEntry[]> {
		return [];
	}

	async getStats(_goblin: string): Promise<any> {
		return { total_tasks: 42, success_rate: 0.98 };
	}

	async getCostSummary(): Promise<CostSummary> {
		return { total_cost: 0.15, cost_by_provider: { demo: 0.15 }, cost_by_model: { "demo-model": 0.15 } };
	}

	async parseOrchestration(text: string, defaultGoblin?: string): Promise<OrchestrationPlan> {
		// Parse the orchestration text to create steps
		const stepTexts = text.split("THEN").map(s => s.trim());
		const steps: OrchestrationStep[] = stepTexts.map((stepText, index) => {
			const [goblin, ...taskParts] = stepText.split(":");
			return {
				id: `step${index + 1}`,
				goblin: goblin?.trim() || defaultGoblin || "docs-writer",
				task: taskParts.join(":").trim(),
				dependencies: index > 0 ? [`step${index}`] : [],
				batch: 0
			};
		});
		return { steps, total_batches: 1, max_parallel: 1 };
	}

	async executeTaskStreaming(
		goblin: string,
		task: string,
		onChunk: (chunk: any) => void,
		onComplete?: (response: any) => void,
		_code?: string,
		_provider?: string,
		_model?: string
	): Promise<void> {
		// Find the appropriate demo response based on the full orchestration
		const fullOrchestration = this.findOrchestrationFromTask(goblin, task);
		const demoData = fullOrchestration ? this.demoResponses[fullOrchestration as keyof typeof this.demoResponses] : null;

		let response: string;
		let cost: number;
		let tokens: number;

		if (demoData && demoData[goblin as keyof typeof demoData]) {
			const stepData = demoData[goblin as keyof typeof demoData] as any;
			response = stepData.response;
			cost = stepData.cost;
			tokens = stepData.tokens;
		} else {
			// Fallback response for unrecognized tasks
			response = `Demo response: ${goblin} completed task "${task}" successfully. This is a pre-recorded demonstration response.`;
			cost = 0.01;
			tokens = 25;
		}

		// Simulate streaming by sending chunks
		const words = response.split(" ");
		let totalTokens = 0;
		let totalCost = 0;

		for (let i = 0; i < words.length; i++) {
			// Simulate realistic typing delay
			await new Promise(resolve => setTimeout(resolve, 30 + Math.random() * 20));

			const chunk = words[i] + (i < words.length - 1 ? " " : "");
			const chunkTokens = Math.ceil(chunk.length / 4); // Rough token estimation
			const chunkCost = (chunkTokens / tokens) * cost;

			totalTokens += chunkTokens;
			totalCost += chunkCost;

			onChunk({
				chunk,
				token_count: chunkTokens,
				cost_delta: chunkCost,
				taskId: `demo_${Date.now()}`,
				provider: "demo",
				model: "demo-model"
			});
		}

		// Send completion
		if (onComplete) {
			onComplete({
				result: response,
				cost: totalCost,
				tokens: totalTokens,
				model: "demo-model",
				provider: "demo",
				duration_ms: words.length * 50
			});
		}
	}

	private findOrchestrationFromTask(goblin: string, task: string): string | null {
		// Try to match the current task to a known orchestration
		for (const [_orchestration, _responses] of Object.entries(this.demoResponses)) {
			if (_orchestration.includes(`${goblin}: ${task}`) || _orchestration.includes(`${goblin}:${task}`)) {
				return _orchestration;
			}
		}
		return null;
	}

	async onTaskStream(_callback: (payload: any) => void) { /* no-op */ }
	async setProviderApiKey(_provider: string, _key: string): Promise<void> { return; }
	async storeApiKey(_provider: string, _key: string): Promise<void> { return; }
	async getApiKey(_provider: string): Promise<string | null> { return "demo-key"; }
	async clearApiKey(_provider: string): Promise<void> { return; }
}

// Mock runtime client for testing when backend is unavailable
export class MockRuntimeClient {
	async getGoblins(): Promise<GoblinStatus[]> {
		return [
			{ id: "docs-writer", name: "docs-writer", title: "Documentation Writer", status: "available" },
			{ id: "code-writer", name: "code-writer", title: "Code Writer", status: "available" }
		];
	}

	async getProviders(): Promise<string[]> {
		return ["openai", "anthropic", "gemini", "ollama"];
	}

	async getProviderModels(provider: string): Promise<string[]> {
		const models: Record<string, string[]> = {
			"openai": ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"],
			"anthropic": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
			"gemini": ["gemini-pro", "gemini-pro-vision"],
			"ollama": ["llama2", "codellama", "mistral"]
		};
		return models[provider] || [];
	}

	async executeTask(
		_goblin: string,
		_task: string,
		_streaming = false,
		_code?: string,
		_provider?: string,
		_model?: string
	): Promise<string> {
		// Simulate async delay
		await new Promise(resolve => setTimeout(resolve, 100));
		return `Executed: ${_task} using ${_goblin}`;
	}

	async getHistory(_goblin: string, _limit = 10): Promise<MemoryEntry[]> {
		return [];
	}

	async getStats(_goblin: string): Promise<any> {
		return { total_tasks: 0, success_rate: 0 };
	}

	async getCostSummary(): Promise<CostSummary> {
		return { total_cost: 0, cost_by_provider: {}, cost_by_model: {} };
	}

	async parseOrchestration(text: string, defaultGoblin?: string): Promise<OrchestrationPlan> {
		// Simple mock parser
		const steps = text.split("THEN").map((step, index) => ({
			id: `step${index + 1}`,
			goblin: defaultGoblin || "docs-writer",
			task: step.trim(),
			dependencies: [],
			batch: 0
		}));
		return { steps, total_batches: 1, max_parallel: 1 };
	}

	async executeTaskStreaming(
		goblin: string,
		task: string,
		onChunk: (chunk: any) => void,
		onComplete?: (response: any) => void,
		_code?: string,
		provider?: string,
		model?: string
	): Promise<void> {
		// Simulate streaming response
		const mockResponse = `Mock response for ${goblin}: ${task}`;
		const words = mockResponse.split(" ");

		for (let i = 0; i < words.length; i++) {
			await new Promise(resolve => setTimeout(resolve, 50));
			onChunk({
				chunk: words[i] + " ",
				token_count: 1,
				cost_delta: 0.001
			});
		}

		if (onComplete) {
			onComplete({
				result: mockResponse,
				cost: words.length * 0.001,
				model: model || "mock-model",
				provider: provider || "mock-provider"
			});
		}
	}

	async onTaskStream(_callback: (payload: any) => void) { /* no-op */ }
	async setProviderApiKey(_provider: string, _key: string): Promise<void> { return; }
	async storeApiKey(_provider: string, _key: string): Promise<void> { return; }
	async getApiKey(_provider: string): Promise<string | null> { return null; }
	async clearApiKey(_provider: string): Promise<void> { return; }
}

export const runtimeClientFast = new FastApiRuntimeClient();
export const runtimeClientMock = new MockRuntimeClient();
export const runtimeClientDemo = new DemoRuntimeClient();

// dynamic selection of runtime client (keep runtimeClient name for compatibility)
export const runtimeClient = MOCK_API
	? (runtimeClientMock as any)
	: (RUNTIME === "demo")
		? (runtimeClientDemo as any)
		: (RUNTIME === "fastapi")
			? (runtimeClientFast as any)
			: (new TauriRuntimeClient() as any);

// export chosen runtime client
export const runtime = runtimeClient;
