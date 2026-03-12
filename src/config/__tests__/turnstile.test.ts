jest.mock('../env', () => ({
  env: {
    turnstile: {
      chat: '0x_test_chat_key',
      login: '0x_test_login_key',
      search: '',
    },
  },
}));
jest.mock('../../utils/dev-log', () => ({
  devError: jest.fn(),
  devWarn: jest.fn(),
}));

import { TURNSTILE_CONFIG, useTurnstile } from '../turnstile';
import { devWarn } from '../../utils/dev-log';

describe('turnstile config', () => {
  it('has chat config enabled with correct key', () => {
    expect(TURNSTILE_CONFIG.chat.enabled).toBe(true);
    expect(TURNSTILE_CONFIG.chat.siteKey).toBe('0x_test_chat_key');
  });

  it('has login config enabled', () => {
    expect(TURNSTILE_CONFIG.login.enabled).toBe(true);
    expect(TURNSTILE_CONFIG.login.siteKey).toBe('0x_test_login_key');
  });

  it('has search config disabled when key is empty', () => {
    expect(TURNSTILE_CONFIG.search.enabled).toBe(false);
  });

  it('useTurnstile returns config for chat', () => {
    const config = useTurnstile('chat');
    expect(config.siteKey).toBe('0x_test_chat_key');
    expect(config.enabled).toBe(true);
  });

  it('useTurnstile warns when not configured', () => {
    useTurnstile('search');
    expect(devWarn).toHaveBeenCalledWith(expect.stringContaining('search'));
  });
});

describe('turnstile key validation', () => {
  it('rejects keys not starting with 0x', () => {
    // Re-import with bad key - done by inline mock override
    jest.resetModules();
    jest.mock('../env', () => ({
      env: {
        turnstile: {
          chat: 'invalid_key',
          login: '',
          search: '',
        },
      },
    }));
    jest.mock('../../utils/dev-log', () => ({
      devError: jest.fn(),
      devWarn: jest.fn(),
    }));
    expect(() => {
      require('../turnstile');
    }).toThrow('Invalid Turnstile configuration');
  });

  it('rejects keys containing secret', () => {
    jest.resetModules();
    jest.mock('../env', () => ({
      env: {
        turnstile: {
          chat: '0x_secret_key',
          login: '',
          search: '',
        },
      },
    }));
    jest.mock('../../utils/dev-log', () => ({
      devError: jest.fn(),
      devWarn: jest.fn(),
    }));
    expect(() => {
      require('../turnstile');
    }).toThrow('Security violation: Secret key in client');
  });
});
