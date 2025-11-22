/**
 * TypeScript definitions for GoblinOS Desktop Tauri commands
 */

import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

// ============================================================================
// Data Types
// ============================================================================

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
}

export interface TaskCost {
	task_id: string;
	provider: string;
	model: string;
	input_tokens: number;
	output_tokens: number;
	input_cost: number;
	output_cost: number;
	total_cost: number;
}

export interface GoblinResponse {
	goblin: string;
	task: string;
	reasoning: string;
	tool?: string;
	command?: string;
	output?: string;
	duration_ms: number;
	cost?: TaskCost;
	model?: string;
}

export interface StreamEvent {
	content: string;
	done: boolean;
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
	total_tasks: number;
	total_input_tokens: number;
	total_output_tokens: number;
	total_cost: number;
	cost_by_provider: Record<string, number>;
	cost_by_model: Record<string, number>;
}

export interface OrchestrationStep {
	id: string;
	goblin_id: string;
	task: string;
	dependencies: string[];
	condition?: string;
	status: "Pending" | "Running" | "Completed" | "Failed" | "Skipped";
	result?: string;
}

export interface OrchestrationPlan {
	id: string;
	description: string;
	steps: OrchestrationStep[];
	status: "Pending" | "Running" | "Completed" | "Failed";
	metadata: {
		total_steps: number;
		parallel_batches: number;
		estimated_duration?: number;
	};
}

// ============================================================================
// Tauri Commands
// ============================================================================

/**
 * Get list of available goblins from goblins.yaml
 */
export async function getGoblins(): Promise<GoblinStatus[]> {
	return invoke<GoblinStatus[]>("get_goblins");
}

/**
 * Get list of available AI providers
 * Returns: ['ollama', 'openai', 'anthropic', 'gemini'] depending on API keys
 */
export async function getProviders(): Promise<string[]> {
	return invoke<string[]>("get_providers");
}

/**
 * Execute a task with a goblin
 * @param request - Goblin ID, task description, and optional streaming flag
 */
export async function executeTask(
	request: ExecuteRequest,
): Promise<GoblinResponse> {
	return invoke<GoblinResponse>("execute_task", { request });
}

/**
 * Get task history for a goblin
 * @param goblin - Goblin ID
 * @param limit - Maximum number of entries to return
 */
export async function getHistory(
	goblin: string,
	limit = 10,
): Promise<MemoryEntry[]> {
	return invoke<MemoryEntry[]>("get_history", { goblin, limit });
}

/**
 * Get statistics for a goblin (including cost summary)
 * @param goblin - Goblin ID
 */
export async function getStats(goblin: string): Promise<any> {
	return invoke("get_stats", { goblin });
}

/**
 * Get cost summary across all tasks
 */
export async function getCostSummary(): Promise<CostSummary> {
	return invoke<CostSummary>("get_cost_summary");
}

/**
 * Parse orchestration syntax into execution plan
 * @param text - Orchestration string (e.g., "task1 THEN task2 AND task3")
 * @param defaultGoblin - Goblin to use if not specified in task
 */
export async function parseOrchestration(
	text: string,
	defaultGoblin?: string,
): Promise<OrchestrationPlan> {
	return invoke<OrchestrationPlan>("parse_orchestration", {
		text,
		defaultGoblin: defaultGoblin || null,
	});
}

// ============================================================================
// Event Listeners
// ============================================================================

/**
 * Listen for streaming token events
 * @param callback - Called for each token chunk
 * @returns Unlisten function to stop listening
 */
export async function onStreamToken(callback: (event: StreamEvent) => void) {
	return listen<StreamEvent>("stream-token", (event) => {
		callback(event.payload);
	});
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Execute task with streaming and receive token-by-token updates
 * @param goblin - Goblin ID
 * @param task - Task description
 * @param onToken - Callback for each token
 * @returns Final response
 */
export async function executeTaskStreaming(
	goblin: string,
	task: string,
	onToken: (token: string) => void,
): Promise<GoblinResponse> {
	let fullResponse = "";

	const unlisten = await onStreamToken((event) => {
		if (!event.done) {
			fullResponse += event.content;
			onToken(event.content);
		}
	});

	try {
		const response = await executeTask({ goblin, task, streaming: true });
		return response;
	} finally {
		unlisten();
	}
}

/**
 * Format cost as USD string
 */
export function formatCost(cost: number): string {
	return `$${cost.toFixed(6)}`;
}

/**
 * Get cost color based on amount
 */
export function getCostColor(cost: number): string {
	if (cost === 0) return "text-green-500";
	if (cost < 0.01) return "text-blue-500";
	if (cost < 0.1) return "text-yellow-500";
	return "text-red-500";
}
