export interface SandboxJob {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  code_snippet?: string;
  language?: string;
}
