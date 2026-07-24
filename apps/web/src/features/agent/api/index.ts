import { apiClient } from '@/lib/api';
import { UiError } from '../../../lib/ui-error';
import { getUserMessage } from '../../../lib/error/toast';
import type {
  AgentTaskEventsResponse,
  AgentTaskRecord,
  AgentTaskSubmitPayload,
  AgentTaskWebhookResponse,
} from '@/lib/api/api-types';

export type {
  AgentTaskEventsResponse,
  AgentTaskRecord,
  AgentTaskSubmitPayload,
  AgentTaskWebhookResponse,
} from '@/lib/api/api-types';

export const submitAgentTask = async (
  payload: AgentTaskSubmitPayload
): Promise<AgentTaskRecord> => {
  try {
    const response = await apiClient.submitAgentTask(payload);
    return response.task;
  } catch (error) {
    throw new UiError(
      {
        code: 'AGENT_TASK_SUBMIT_FAILED',
        userMessage: getUserMessage(error),
      },
      error
    );
  }
};

export const getAgentTask = async (taskId: string): Promise<AgentTaskRecord> => {
  try {
    return await apiClient.getAgentTask(taskId);
  } catch (error) {
    throw new UiError(
      {
        code: 'AGENT_TASK_LOAD_FAILED',
        userMessage: getUserMessage(error),
      },
      error
    );
  }
};

export const getAgentTaskEvents = async (taskId: string): Promise<AgentTaskEventsResponse> => {
  try {
    return await apiClient.getAgentTaskEvents(taskId);
  } catch (error) {
    throw new UiError(
      {
        code: 'AGENT_TASK_EVENTS_FAILED',
        userMessage: getUserMessage(error),
      },
      error
    );
  }
};

export const submitGithubIssueWebhook = async (
  payload: Record<string, unknown>
): Promise<AgentTaskWebhookResponse> => {
  try {
    return await apiClient.submitGithubIssueWebhook(payload);
  } catch (error) {
    throw new UiError(
      {
        code: 'AGENT_GITHUB_WEBHOOK_FAILED',
        userMessage: getUserMessage(error),
      },
      error
    );
  }
};
