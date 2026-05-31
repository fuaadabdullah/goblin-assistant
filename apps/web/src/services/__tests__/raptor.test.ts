import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import MockAdapter from 'axios-mock-adapter';

jest.mock('../../utils/auth-session', () => ({
  getRefreshToken: jest.fn(() => null),
  getAuthToken: jest.fn(() => null),
  persistAuthSession: jest.fn(),
  clearAuthSession: jest.fn(),
}));

import { backendHttp } from '../../lib/api/shared';
import * as raptorService from '../raptor';

let mock: MockAdapter;

beforeEach(() => {
  mock = new MockAdapter(backendHttp);
});

afterEach(() => {
  mock.restore();
});

describe('raptor service', () => {
  describe('raptorStart', () => {
    it('should call POST /raptor/start', async () => {
      mock.onPost('/raptor/start').reply(200);

      await raptorService.raptorStart();

      expect(mock.history.post.some((r) => r.url === '/raptor/start')).toBe(true);
    });

    it('should propagate errors from the API', async () => {
      mock.onPost('/raptor/start').reply(500, { detail: 'Start failed' });

      await expect(raptorService.raptorStart()).rejects.toThrow('Start failed');
    });
  });

  describe('raptorStop', () => {
    it('should call POST /raptor/stop', async () => {
      mock.onPost('/raptor/stop').reply(200);

      await raptorService.raptorStop();

      expect(mock.history.post.some((r) => r.url === '/raptor/stop')).toBe(true);
    });
  });

  describe('raptorStatus', () => {
    it('should fetch current Raptor status', async () => {
      const mockStatus: raptorService.RaptorStatus = {
        running: true,
        config_file: '/path/to/config.yaml',
      };
      mock.onGet('/raptor/status').reply(200, mockStatus);

      const status = await raptorService.raptorStatus();

      expect(status).toEqual(mockStatus);
    });

    it('should propagate API errors', async () => {
      mock.onGet('/raptor/status').reply(503, { detail: 'Service unavailable' });

      await expect(raptorService.raptorStatus()).rejects.toThrow();
    });
  });

  describe('raptorLogs', () => {
    it('should fetch Raptor logs', async () => {
      const mockLogs: raptorService.RaptorLogsResponse = {
        log_tail: '2026-02-18 10:00:00 INFO Raptor started\n2026-02-18 10:00:01 INFO Ready',
      };
      mock.onGet('/raptor/logs').reply(200, mockLogs);

      const logs = await raptorService.raptorLogs();

      expect(logs).toEqual(mockLogs);
    });
  });

  describe('raptorDemo', () => {
    it('should run a Raptor demo with specified mode', async () => {
      mock.onPost('/raptor/demo/embeddings').reply(200);

      await raptorService.raptorDemo('embeddings');

      expect(mock.history.post.some((r) => r.url === '/raptor/demo/embeddings')).toBe(true);
    });

    it('should support different demo modes', async () => {
      mock.onPost('/raptor/demo/chat').reply(200);

      await raptorService.raptorDemo('chat');

      expect(mock.history.post.some((r) => r.url === '/raptor/demo/chat')).toBe(true);
    });
  });
});
