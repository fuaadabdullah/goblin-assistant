import { getFrontend, postFrontend } from './shared';
import type {
  AgentTaskEventsResponse,
  AgentTaskRecord,
  AgentTaskSubmitPayload,
  AgentTaskStatusResponse,
  AgentTaskWebhookResponse,
} from './api-types';

const INTERNAL_AGENT_PREFIX = '/api/agent';

export const agentMethods = {
  async submitAgentTask(payload: AgentTaskSubmitPayload): Promise<AgentTaskStatusResponse> {
    return postFrontend<AgentTaskStatusResponse, AgentTaskSubmitPayload>(
      `${INTERNAL_AGENT_PREFIX}/task`,
      payload
    );
  },

  async getAgentTask(taskId: string): Promise<AgentTaskRecord> {
    return getFrontend<AgentTaskRecord>(`${INTERNAL_AGENT_PREFIX}/task/${encodeURIComponent(taskId)}`);
  },

  async getAgentTaskEvents(taskId: string): Promise<AgentTaskEventsResponse> {
    return getFrontend<AgentTaskEventsResponse>(
      `${INTERNAL_AGENT_PREFIX}/task/${encodeURIComponent(taskId)}/events`
    );
  },

  async submitGithubIssueWebhook(payload: Record<string, unknown>): Promise<AgentTaskWebhookResponse> {
    return postFrontend<AgentTaskWebhookResponse, Record<string, unknown>>(
      `${INTERNAL_AGENT_PREFIX}/task/github-webhook`,
      payload
    );
  },
};
