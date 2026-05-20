import type { StartupDiagnostics } from '../../../utils/startup-diagnostics';
import type { ModuleFlags } from '../../../config/features';

export type StartupStatus =
  | 'checking-auth'
  | 'loading-config'
  | 'initializing-runtime'
  | 'ready'
  | 'error';

export interface StartupState {
  status: StartupStatus;
  message: string;
  destinationRoute?: string;
  logId?: string;
  diagnostics?: StartupDiagnostics;
  modules?: ModuleFlags;
}
