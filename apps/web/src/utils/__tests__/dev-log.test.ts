import { devDebug, devError, devInfo, devLog, devWarn } from '../dev-log';

describe('development logging utilities', () => {
  const originalNodeEnv = process.env.NODE_ENV;
  let consoleLogSpy: vi.SpyInstance;
  let consoleInfoSpy: vi.SpyInstance;
  let consoleWarnSpy: vi.SpyInstance;
  let consoleErrorSpy: vi.SpyInstance;
  let consoleDebugSpy: vi.SpyInstance;

  beforeEach(() => {
    consoleLogSpy = vi.spyOn(console, 'log').mockImplementation();
    consoleInfoSpy = vi.spyOn(console, 'info').mockImplementation();
    consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation();
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation();
    consoleDebugSpy = vi.spyOn(console, 'debug').mockImplementation();
  });

  afterEach(() => {
    process.env.NODE_ENV = originalNodeEnv;
    consoleLogSpy.mockRestore();
    consoleInfoSpy.mockRestore();
    consoleWarnSpy.mockRestore();
    consoleErrorSpy.mockRestore();
    consoleDebugSpy.mockRestore();
  });

  it('emits all dev helpers outside production', () => {
    process.env.NODE_ENV = 'development';

    devLog('log');
    devInfo('info');
    devWarn('warn');
    devError('error');
    devDebug('debug');

    expect(consoleLogSpy).toHaveBeenCalledWith('log');
    expect(consoleInfoSpy).toHaveBeenCalledWith('info');
    expect(consoleWarnSpy).toHaveBeenCalledWith('warn');
    expect(consoleErrorSpy).toHaveBeenCalledWith('error');
    expect(consoleDebugSpy).toHaveBeenCalledWith('debug');
  });

  it('suppresses all dev helpers in production', () => {
    process.env.NODE_ENV = 'production';

    devLog('log');
    devInfo('info');
    devWarn('warn');
    devError('error');
    devDebug('debug');

    expect(consoleLogSpy).not.toHaveBeenCalled();
    expect(consoleInfoSpy).not.toHaveBeenCalled();
    expect(consoleWarnSpy).not.toHaveBeenCalled();
    expect(consoleErrorSpy).not.toHaveBeenCalled();
    expect(consoleDebugSpy).not.toHaveBeenCalled();
  });
});
