import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import * as raptorService from '../raptor';
import { api } from '@/api';

const postSpy = jest.spyOn(api, 'post');
const getSpy = jest.spyOn(api, 'get');

describe('raptor service', () => {
  beforeEach(() => {
    postSpy.mockReset();
    getSpy.mockReset();
  });

  describe('raptorStart', () => {
    it('should call POST /raptor/start', async () => {
      postSpy.mockResolvedValue(undefined as unknown as { data: unknown });

      await raptorService.raptorStart();

      expect(postSpy).toHaveBeenCalledWith('/raptor/start');
    });

    it('should handle errors from the API', async () => {
      const error = new Error('Start failed');
      postSpy.mockRejectedValue(error);

      await expect(raptorService.raptorStart()).rejects.toThrow('Start failed');
    });
  });

  describe('raptorStop', () => {
    it('should call POST /raptor/stop', async () => {
      postSpy.mockResolvedValue(undefined as unknown as { data: unknown });

      await raptorService.raptorStop();

      expect(postSpy).toHaveBeenCalledWith('/raptor/stop');
    });
  });

  describe('raptorStatus', () => {
    it('should fetch current Raptor status', async () => {
      const mockStatus: raptorService.RaptorStatus = {
        running: true,
        config_file: '/path/to/config.yaml',
      };

      getSpy.mockResolvedValue({ data: mockStatus });

      const status = await raptorService.raptorStatus();

      expect(status).toEqual(mockStatus);
      expect(getSpy).toHaveBeenCalledWith('/raptor/status');
    });

    it('should handle API errors', async () => {
      getSpy.mockRejectedValue(new Error('Status check failed'));

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

      getSpy.mockResolvedValue({ data: mockLogs });

      const logs = await raptorService.raptorLogs();

      expect(logs).toEqual(mockLogs);
      expect(getSpy).toHaveBeenCalledWith('/raptor/logs');
    });
  });

  describe('raptorDemo', () => {
    it('should run a Raptor demo with specified mode', async () => {
      postSpy.mockResolvedValue(undefined as unknown as { data: unknown });

      await raptorService.raptorDemo('embeddings');

      expect(postSpy).toHaveBeenCalledWith('/raptor/demo/embeddings');
    });

    it('should support different demo modes', async () => {
      postSpy.mockResolvedValue(undefined as unknown as { data: unknown });

      await raptorService.raptorDemo('chat');

      expect(postSpy).toHaveBeenCalledWith('/raptor/demo/chat');
    });
  });
});
