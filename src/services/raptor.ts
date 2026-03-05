import { api } from '../api/http-client';

/**
 * Raptor Mini service - controls the local Raptor LLM assistant
 */

export interface RaptorStatus {
  running: boolean;
  config_file?: string;
}

export interface RaptorLogsResponse {
  log_tail: string;
}

/**
 * Start the Raptor Mini service
 */
export async function raptorStart(): Promise<void> {
  await api.post('/raptor/start');
}

/**
 * Stop the Raptor Mini service
 */
export async function raptorStop(): Promise<void> {
  await api.post('/raptor/stop');
}

/**
 * Get current Raptor status
 */
export async function raptorStatus(): Promise<RaptorStatus> {
  const response = await api.get<RaptorStatus>('/raptor/status');
  return response.data;
}

/**
 * Get Raptor logs
 */
export async function raptorLogs(): Promise<RaptorLogsResponse> {
  const response = await api.get<RaptorLogsResponse>('/raptor/logs');
  return response.data;
}

/**
 * Run a Raptor demo
 */
export async function raptorDemo(mode: string): Promise<void> {
  await api.post(`/raptor/demo/${mode}`);
}
