import { getFrontend, postFrontend } from '@/lib/api';

export interface RaptorStatus {
  running: boolean;
  config_file?: string;
}

export interface RaptorLogsResponse {
  log_tail: string;
}

export async function raptorStart(): Promise<void> {
  await postFrontend('/api/raptor/start');
}

export async function raptorStop(): Promise<void> {
  await postFrontend('/api/raptor/stop');
}

export async function raptorStatus(): Promise<RaptorStatus> {
  return getFrontend<RaptorStatus>('/api/raptor/status');
}

export async function raptorLogs(): Promise<RaptorLogsResponse> {
  return getFrontend<RaptorLogsResponse>('/api/raptor/logs');
}

export async function raptorDemo(mode: string): Promise<void> {
  await postFrontend(`/api/raptor/demo/${mode}`);
}
