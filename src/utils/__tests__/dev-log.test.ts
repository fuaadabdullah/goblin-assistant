import {
  devDebug,
  devError,
  devInfo,
  devLog,
  devWarn,
} from '../dev-log';

describe('development logging utilities', () => {
  const originalNodeEnv = process.env.NODE_ENV;
  let consoleLogSpy: jest.SpyInstance;
  let consoleInfoSpy: jest.SpyInstance;
  let consoleWarnSpy: jest.SpyInstance;
  let consoleErrorSpy: jest.SpyInstance;
  let consoleDebugSpy: jest.SpyInstance;

  beforeEach(() => {
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();
    consoleInfoSpy = jest.spyOn(console, 'info').mockImplementation();
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    consoleDebugSpy = jest.spyOn(console, 'debug').mockImplementation();
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
