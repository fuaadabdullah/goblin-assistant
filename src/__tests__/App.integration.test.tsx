import { describe, expect, it, vi } from "vitest";

// Mock the runtimeClient used by tests
vi.mock("../api/tauri-client", () => {
	return {
		runtimeClient: {
			getGoblins: async () => [
				{
					id: "codesmith",
					name: "CodeSmith",
					title: "Coder",
					status: "active",
					brain: { router: "openai" },
				},
			],
			getProviders: async () => ["ollama", "openai"],
			getCostSummary: async () => ({
				total_cost: 0,
				cost_by_provider: {},
				cost_by_model: {},
			}),
			executeTask: async (g: string, t: string) => ({
				goblin: g,
				task: t,
				reasoning: "done",
				duration_ms: 10,
			}),
			executeTaskStreaming: async (
				_g: string,
				_t: string,
				onChunk: (c: string) => void,
				onComplete?: any,
			) => {
				// simulate streaming tokens
				onChunk("hello ");
				onChunk("world");
				if (onComplete) onComplete({ reasoning: "hello world" });
			},
			parseOrchestration: async (_text: string) => ({
				steps: [],
				total_batches: 0,
				max_parallel: 0,
			}),
		},
	};
});

import { runtimeClient } from "../api/tauri-client";

describe("runtimeClient smoke (mocked)", () => {
	it("returns goblins with brain.router and providers", async () => {
		const goblins = await runtimeClient.getGoblins();
		// GoblinStatus may not declare `brain` in the test typings; cast to any for the assertion
		expect((goblins[0] as any).brain?.router).toBe("openai");
		const providers = await runtimeClient.getProviders();
		expect(providers).toContain("openai");
	});

	it("simulate streaming execution collects tokens and final response", async () => {
		const chunks: string[] = [];
		await runtimeClient.executeTaskStreaming(
			"codesmith",
			"Say hi",
			(token: string) => chunks.push(token),
			(finalResponse: any) => {
				// finalResponse.reasoning should be combined
				expect(finalResponse.reasoning).toBe("hello world");
			},
		);

		expect(chunks.join("")).toBe("hello world");
	});
});
