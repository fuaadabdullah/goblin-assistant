import { V1_API_PREFIX, postBackend } from './shared';

export interface TriageResult {
  title: string;
  category: string;
  priority: string;
  affected_service: string;
  stack_trace: string | null;
  cleaned_description: string;
}

export interface TriageResponse {
  id: string;
  triage: TriageResult;
  issue_url: string | null;
  issue_number: number | null;
}

export const supportMethods = {
  async sendSupportMessage(message: string) {
    return postBackend(`${V1_API_PREFIX}/support/message`, { message });
  },

  async triageIssue(description: string, context?: string): Promise<{ data: TriageResponse }> {
    return postBackend(`${V1_API_PREFIX}/support/triage`, { description, context });
  },
};
