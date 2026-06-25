import { V1_API_PREFIX, getBackend, postBackend } from '@/lib/api';

export interface RaptorStatus {
  running: boolean;
  config_file?: string;
}

export interface RaptorLogsResponse {
  log_tail: string;
}

export async function raptorStart(): Promise<void> {
  await postBackend(`${V1_API_PREFIX}/raptor/start`);
}

export async function raptorStop(): Promise<void> {
  await postBackend(`${V1_API_PREFIX}/raptor/stop`);
}

export async function raptorStatus(): Promise<RaptorStatus> {
  return getBackend<RaptorStatus>(`${V1_API_PREFIX}/raptor/status`);
}

export async function raptorLogs(): Promise<RaptorLogsResponse> {
  return getBackend<RaptorLogsResponse>(`${V1_API_PREFIX}/raptor/logs`);
}

export async function raptorDemo(mode: string): Promise<void> {
  await postBackend(`${V1_API_PREFIX}/raptor/demo/${mode}`);
}
