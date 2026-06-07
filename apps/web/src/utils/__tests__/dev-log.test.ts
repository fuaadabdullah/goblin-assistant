import { devError, devWarn } from '../dev-log';

describe('development logging utilities', () => {
  const originalNodeEnv = process.env.NODE_ENV;
  let consoleWarnSpy: vi.SpyInstance;
  let consoleErrorSpy: vi.SpyInstance;

  beforeEach(() => {
    consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation();
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation();
  });

  afterEach(() => {
    process.env.NODE_ENV = originalNodeEnv;
    consoleWarnSpy.mockRestore();
    consoleErrorSpy.mockRestore();
  });

  it('emits devWarn and devError outside production', () => {
    process.env.NODE_ENV = 'development';

    devWarn('warn');
    devError('error');

    expect(consoleWarnSpy).toHaveBeenCalledWith('warn');
    expect(consoleErrorSpy).toHaveBeenCalledWith('error');
  });

  it('suppresses devWarn and devError in production', () => {
    process.env.NODE_ENV = 'production';

    devWarn('warn');
    devError('error');

    expect(consoleWarnSpy).not.toHaveBeenCalled();
    expect(consoleErrorSpy).not.toHaveBeenCalled();
  });
});