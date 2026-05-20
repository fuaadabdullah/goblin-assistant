import { describe, it, expect, beforeEach, afterEach, afterAll, jest } from '@jest/globals';
import { render, screen, waitFor } from '@testing-library/react';
import type { ErrorBoundaryRenderProps } from '../ErrorBoundary';

jest.mock('../../utils/monitoring', () => ({
  logErrorToService: jest.fn(),
  reactErrorInfoToContext: jest.fn(() => ({ componentStack: 'at Thrower' })),
}));

const { ErrorBoundary } = require('../ErrorBoundary') as typeof import('../ErrorBoundary');
const { env } = require('../../config/env') as typeof import('../../config/env');
const monitoring = require('../../utils/monitoring') as {
  logErrorToService: jest.Mock;
  reactErrorInfoToContext: jest.Mock;
};

const Thrower = ({
  message = 'Render exploded',
  stack = 'stack trace',
}: {
  message?: string;
  stack?: string;
}) => {
  const error = new Error(message);
  error.stack = stack;
  throw error;
};

describe('ErrorBoundary', () => {
  const originalEnv = { ...env };
  const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

  beforeEach(() => {
    jest.clearAllMocks();
    env.isDevelopment = false;
    env.isProduction = true;
    env.mode = 'production';
    env.sentryDsn = 'https://example@sentry.test/1';
  });

  afterEach(() => {
    env.isDevelopment = originalEnv.isDevelopment;
    env.isProduction = originalEnv.isProduction;
    env.mode = originalEnv.mode;
    env.sentryDsn = originalEnv.sentryDsn;
  });

  it('captures render errors and passes the error and event ID to fallbackRender', async () => {
    monitoring.logErrorToService.mockReturnValue('evt-123');

    const fallbackRender = jest.fn(({ error, errorId }: ErrorBoundaryRenderProps) => (
      <div>{`${error.message}:${errorId ?? 'missing'}`}</div>
    ));

    render(
      <ErrorBoundary boundaryName="route:chat" fallbackRender={fallbackRender}>
        <Thrower message="chat crashed" />
      </ErrorBoundary>
    );

    await waitFor(() => {
      expect(screen.getByText('chat crashed:evt-123')).toBeInTheDocument();
    });

    expect(monitoring.logErrorToService).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'chat crashed' }),
      expect.objectContaining({ boundaryName: 'route:chat' })
    );
    expect(monitoring.reactErrorInfoToContext).toHaveBeenCalled();
    expect(fallbackRender).toHaveBeenLastCalledWith(
      expect.objectContaining({
        error: expect.objectContaining({ message: 'chat crashed' }),
        errorId: 'evt-123',
        reset: expect.any(Function),
      })
    );
  });

  it('passes no error ID when Sentry does not return one', async () => {
    monitoring.logErrorToService.mockReturnValue(undefined);

    const fallbackRender = jest.fn(({ error, errorId }: ErrorBoundaryRenderProps) => (
      <div>{`${error.message}:${errorId ?? 'missing'}`}</div>
    ));

    render(
      <ErrorBoundary fallbackRender={fallbackRender}>
        <Thrower message="settings crashed" />
      </ErrorBoundary>
    );

    await waitFor(() => {
      expect(screen.getByText('settings crashed:missing')).toBeInTheDocument();
    });

    expect(fallbackRender).toHaveBeenLastCalledWith(
      expect.objectContaining({
        errorId: undefined,
      })
    );
  });

  it('hides stack traces in production while still showing a support reference', async () => {
    monitoring.logErrorToService.mockReturnValue('evt-prod');

    render(
      <ErrorBoundary>
        <Thrower message="prod crash" stack="top secret stack trace" />
      </ErrorBoundary>
    );

    await waitFor(() => {
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    });

    expect(screen.getByText(/Reference ID:/)).toBeInTheDocument();
    expect(screen.getByText('prod crash')).toBeInTheDocument();
    expect(screen.queryByText(/top secret stack trace/)).not.toBeInTheDocument();
  });

  afterAll(() => {
    consoleErrorSpy.mockRestore();
  });
});
