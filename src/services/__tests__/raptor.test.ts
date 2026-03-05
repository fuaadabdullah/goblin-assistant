import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import * as raptorService from '../raptor';

// Mock the api module
jest.mock('../../api/http-client', () => ({
  api: {
    post: jest.fn(),
    get: jest.fn(),
  },
}));

const mockApi = require('../../api/http-client').api;

describe('raptor service', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('raptorStart', () => {
    it('should call POST /raptor/start', async () => {
      mockApi.post.mockResolvedValue(undefined);

      await raptorService.raptorStart();

      expect(mockApi.post).toHaveBeenCalledWith('/raptor/start');
    });

    it('should handle errors from the API', async () => {
      const error = new Error('Start failed');
      mockApi.post.mockRejectedValue(error);

      await expect(raptorService.raptorStart()).rejects.toThrow('Start failed');
    });
  });

  describe('raptorStop', () => {
    it('should call POST /raptor/stop', async () => {
      mockApi.post.mockResolvedValue(undefined);

      await raptorService.raptorStop();

      expect(mockApi.post).toHaveBeenCalledWith('/raptor/stop');
    });
  });

  describe('raptorStatus', () => {
    it('should fetch current Raptor status', async () => {
      const mockStatus: raptorService.RaptorStatus = {
        running: true,
        config_file: '/path/to/config.yaml',
      };

      mockApi.get.mockResolvedValue({ data: mockStatus });

      const status = await raptorService.raptorStatus();

      expect(status).toEqual(mockStatus);
      expect(mockApi.get).toHaveBeenCalledWith('/raptor/status');
    });

    it('should handle API errors', async () => {
      mockApi.get.mockRejectedValue(new Error('Status check failed'));

      await expect(raptorService.raptorStatus()).rejects.toThrow(
        'Status check failed',
      );
    });
  });

  describe('raptorLogs', () => {
    it('should fetch Raptor logs', async () => {
      const mockLogs: raptorService.RaptorLogsResponse = {
        log_tail:
          '2026-02-18 10:00:00 INFO Raptor started\n2026-02-18 10:00:01 INFO Ready',
      };

      mockApi.get.mockResolvedValue({ data: mockLogs });

      const logs = await raptorService.raptorLogs();

      expect(logs).toEqual(mockLogs);
      expect(mockApi.get).toHaveBeenCalledWith('/raptor/logs');
    });
  });

  describe('raptorDemo', () => {
    it('should run a Raptor demo with specified mode', async () => {
      mockApi.post.mockResolvedValue(undefined);

      await raptorService.raptorDemo('embeddings');

      expect(mockApi.post).toHaveBeenCalledWith('/raptor/demo/embeddings');
    });

    it('should support different demo modes', async () => {
      mockApi.post.mockResolvedValue(undefined);

      await raptorService.raptorDemo('chat');

      expect(mockApi.post).toHaveBeenCalledWith('/raptor/demo/chat');
    });
  });
});
