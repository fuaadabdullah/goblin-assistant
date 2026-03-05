export type StartupDiagnosticStatus =
  | 'checking-auth'
  | 'loading-config'
  | 'initializing-runtime'
  | 'ready'
  | 'error';

export interface StartupDiagnostics {
  logId: string;
  status: StartupDiagnosticStatus;
  message: string;
  timestamp: string;
  authMs?: number;
  configMs?: number;
  runtimeMs?: number;
  totalMs?: number;
}

const STORAGE_KEY = 'goblin_startup_diagnostics';

export const storeStartupDiagnostics = (payload: StartupDiagnostics): void => {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch (error) {
    console.warn('Failed to store startup diagnostics:', error);
  }
};

export const readStartupDiagnostics = (): StartupDiagnostics | null => {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return null;
    return parsed as StartupDiagnostics;
  } catch (error) {
    console.warn('Failed to read startup diagnostics:', error);
    return null;
  }
};

export const clearStartupDiagnostics = (): void => {
  if (typeof window === 'undefined') return;
  try {
    window.sessionStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.warn('Failed to clear startup diagnostics:', error);
  }
};
