import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

jest.mock('next/link', () => function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
  return <a href={href}>{children}</a>;
});
jest.mock('../../../../components/Seo', () => function MockSeo() { return null; });

import HelpView from '../HelpView';

jest.mock('../HelpTopics', () => function MockHelpTopics({ topics }: { topics: Array<{ title: string }> }) {
  return <div data-testid="help-topics">{topics.map(t => <div key={t.title}>{t.title}</div>)}</div>;
});
jest.mock('../HelpSupportForm', () => function MockForm({ message, onSubmit, onMessageChange }: {
  message: string; onSubmit: () => void; onMessageChange: (v: string) => void;
}) {
  return (
    <div data-testid="support-form">
      <input value={message} onChange={e => onMessageChange(e.target.value)} data-testid="msg-input" />
      <button onClick={onSubmit} data-testid="submit-btn">Submit</button>
    </div>
  );
});

const defaultForm = {
  message: '',
  sent: false,
  error: null,
  sending: false,
  setMessage: jest.fn(),
  handleSubmit: jest.fn(),
};

describe('HelpView', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders heading', () => {
    render(<HelpView form={defaultForm} />);
    expect(screen.getByText('Support & Docs')).toBeInTheDocument();
  });

  it('renders subtitle', () => {
    render(<HelpView form={defaultForm} />);
    expect(screen.getByText(/Gateway setup, routing/)).toBeInTheDocument();
  });

  it('renders help topics', () => {
    render(<HelpView form={defaultForm} />);
    expect(screen.getByTestId('help-topics')).toBeInTheDocument();
    expect(screen.getByText('Getting started')).toBeInTheDocument();
    expect(screen.getByText('Search tips')).toBeInTheDocument();
    expect(screen.getByText('Safe experiments')).toBeInTheDocument();
  });

  it('renders support form', () => {
    render(<HelpView form={defaultForm} />);
    expect(screen.getByTestId('support-form')).toBeInTheDocument();
  });

  it('does not show startup failure when absent', () => {
    render(<HelpView form={defaultForm} />);
    expect(screen.queryByText('Startup issue detected')).not.toBeInTheDocument();
  });

  it('shows startup failure section', () => {
    const failure = {
      logId: 'log-123',
      diagnostics: {
        status: 'failed',
        message: 'Config error',
        authMs: 50,
        configMs: 100,
        runtimeMs: 200,
        totalMs: 350,
        timestamp: '2024-01-01T00:00:00Z',
        logId: 'diag-456',
      },
      onRetry: jest.fn(),
    };
    render(<HelpView form={defaultForm} startupFailure={failure} />);
    expect(screen.getByText('Startup issue detected')).toBeInTheDocument();
    expect(screen.getByText(/Config error/)).toBeInTheDocument();
    expect(screen.getByText('log-123')).toBeInTheDocument();
  });

  it('shows diagnostic metrics', () => {
    const failure = {
      diagnostics: {
        status: 'failed',
        message: 'err',
        authMs: 10,
        configMs: 20,
        runtimeMs: 30,
        totalMs: 60,
        timestamp: '2024-01-01',
      },
      onRetry: jest.fn(),
    };
    render(<HelpView form={defaultForm} startupFailure={failure} />);
    expect(screen.getByText(/Auth:.*10/)).toBeInTheDocument();
    expect(screen.getByText(/Config:.*20/)).toBeInTheDocument();
  });

  it('shows fallback values when diagnostics are null', () => {
    const failure = { onRetry: jest.fn() };
    render(<HelpView form={defaultForm} startupFailure={failure} />);
    expect(screen.getByText('Startup issue detected')).toBeInTheDocument();
    expect(screen.getAllByText(/unknown/).length).toBeGreaterThanOrEqual(1);
  });

  it('calls onRetry when retry button clicked', () => {
    const onRetry = jest.fn();
    const failure = { onRetry };
    render(<HelpView form={defaultForm} startupFailure={failure} />);
    fireEvent.click(screen.getByText('Retry boot'));
    expect(onRetry).toHaveBeenCalled();
  });

  it('shows logId from diagnostics when startupFailure.logId absent', () => {
    const failure = {
      diagnostics: {
        status: 'failed',
        message: 'err',
        authMs: 0,
        configMs: 0,
        runtimeMs: 0,
        totalMs: 0,
        timestamp: '2024-01-01',
        logId: 'diag-log-789',
      },
      onRetry: jest.fn(),
    };
    render(<HelpView form={defaultForm} startupFailure={failure} />);
    expect(screen.getByText('diag-log-789')).toBeInTheDocument();
  });
});
