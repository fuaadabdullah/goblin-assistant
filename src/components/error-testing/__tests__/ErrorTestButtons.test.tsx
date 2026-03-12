import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

jest.mock('../../ui/Button', () => function MockButton({ children, onClick, disabled, variant }: { children: React.ReactNode; onClick: () => void; disabled?: boolean; variant?: string }) {
  return <button onClick={onClick} disabled={disabled} data-variant={variant}>{children}</button>;
});

import { ErrorTestButtons } from '../../error-testing/ErrorTestButtons';

const defaultProps = {
  onJavaScriptError: jest.fn(),
  onTypeError: jest.fn(),
  onCustomError: jest.fn(),
  onAsyncError: jest.fn(),
  onNetworkError: jest.fn(),
  onUnhandledPromiseRejection: jest.fn(),
  onSentryError: jest.fn(),
  onSentryMessage: jest.fn(),
  onSentryBreadcrumb: jest.fn(),
  onRunAll: jest.fn(),
  running: false,
};

describe('ErrorTestButtons', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders all 10 buttons', () => {
    render(<ErrorTestButtons {...defaultProps} />);
    expect(screen.getAllByRole('button')).toHaveLength(10);
  });

  it('renders JavaScript Error button', () => {
    render(<ErrorTestButtons {...defaultProps} />);
    expect(screen.getByText('JavaScript Error')).toBeInTheDocument();
  });

  it('renders Type Error button', () => {
    render(<ErrorTestButtons {...defaultProps} />);
    expect(screen.getByText('Type Error')).toBeInTheDocument();
  });

  it('renders Run All Tests button', () => {
    render(<ErrorTestButtons {...defaultProps} />);
    expect(screen.getByText('Run All Tests')).toBeInTheDocument();
  });

  it('calls respective handler on click', () => {
    render(<ErrorTestButtons {...defaultProps} />);
    fireEvent.click(screen.getByText('JavaScript Error'));
    expect(defaultProps.onJavaScriptError).toHaveBeenCalled();
  });

  it('calls onRunAll on Run All Tests click', () => {
    render(<ErrorTestButtons {...defaultProps} />);
    fireEvent.click(screen.getByText('Run All Tests'));
    expect(defaultProps.onRunAll).toHaveBeenCalled();
  });

  it('disables all buttons when running', () => {
    render(<ErrorTestButtons {...defaultProps} running={true} />);
    screen.getAllByRole('button').forEach((btn) => {
      expect(btn).toBeDisabled();
    });
  });

  it('enables all buttons when not running', () => {
    render(<ErrorTestButtons {...defaultProps} running={false} />);
    screen.getAllByRole('button').forEach((btn) => {
      expect(btn).not.toBeDisabled();
    });
  });

  it('renders Sentry buttons', () => {
    render(<ErrorTestButtons {...defaultProps} />);
    expect(screen.getByText('Sentry Error')).toBeInTheDocument();
    expect(screen.getByText('Sentry Message')).toBeInTheDocument();
    expect(screen.getByText('Sentry Breadcrumb')).toBeInTheDocument();
  });

  it('calls onNetworkError on click', () => {
    render(<ErrorTestButtons {...defaultProps} />);
    fireEvent.click(screen.getByText('Network Error'));
    expect(defaultProps.onNetworkError).toHaveBeenCalled();
  });
});
