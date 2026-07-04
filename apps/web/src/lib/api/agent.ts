import { V1_API_PREFIX, getBackend, postBackend } from './shared';
import type {
  AgentTaskEventsResponse,
  AgentTaskRecord,
  AgentTaskSubmitPayload,
  AgentTaskStatusResponse,
  AgentTaskWebhookResponse,
} from './api-types';

export const agentMethods = {
  async submitAgentTask(payload: AgentTaskSubmitPayload): Promise<AgentTaskStatusResponse> {
    return postBackend<AgentTaskStatusResponse, AgentTaskSubmitPayload>(
      `${V1_API_PREFIX}/agent/task`,
      payload
    );
  },

  async getAgentTask(taskId: string): Promise<AgentTaskRecord> {
    return getBackend<AgentTaskRecord>(
      `${V1_API_PREFIX}/agent/task/${encodeURIComponent(taskId)}`
    );
  },

  async getAgentTaskEvents(taskId: string): Promise<AgentTaskEventsResponse> {
    return getBackend<AgentTaskEventsResponse>(
      `${V1_API_PREFIX}/agent/task/${encodeURIComponent(taskId)}/events`
    );
  },

  async submitGithubIssueWebhook(payload: Record<string, unknown>): Promise<AgentTaskWebhookResponse> {
    return postBackend<AgentTaskWebhookResponse, Record<string, unknown>>(
      `${V1_API_PREFIX}/agent/task/github-webhook`,
      payload
    );
  },
};
