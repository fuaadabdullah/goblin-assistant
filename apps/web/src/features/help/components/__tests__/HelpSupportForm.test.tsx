import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

jest.mock('next/link', () =>
  function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
    return <a href={href}>{children}</a>;
  }
);

import HelpSupportForm from '../HelpSupportForm';

describe('HelpSupportForm', () => {
  const defaultProps = {
    message: '',
    sent: false,
    onMessageChange: jest.fn(),
    onSubmit: jest.fn(),
  };

  beforeEach(() => jest.clearAllMocks());

  it('renders heading', () => {
    render(<HelpSupportForm {...defaultProps} />);
    expect(screen.getByText('Chat with Support')).toBeInTheDocument();
  });

  it('renders description text', () => {
    render(<HelpSupportForm {...defaultProps} />);
    expect(screen.getByText(/Describe the issue/)).toBeInTheDocument();
  });

  it('renders textarea with placeholder', () => {
    render(<HelpSupportForm {...defaultProps} />);
    expect(screen.getByPlaceholderText(/Tell us what you need help with/)).toBeInTheDocument();
  });

  it('renders textarea with message value', () => {
    render(<HelpSupportForm {...defaultProps} message="My problem" />);
    expect(screen.getByDisplayValue('My problem')).toBeInTheDocument();
  });

  it('calls onMessageChange when typing', () => {
    render(<HelpSupportForm {...defaultProps} />);
    fireEvent.change(screen.getByPlaceholderText(/Tell us/), { target: { value: 'new msg' } });
    expect(defaultProps.onMessageChange).toHaveBeenCalledWith('new msg');
  });

  it('renders submit button', () => {
    render(<HelpSupportForm {...defaultProps} />);
    expect(screen.getByText('Send to Support')).toBeInTheDocument();
  });

  it('shows Sending... when sending', () => {
    render(<HelpSupportForm {...defaultProps} sending />);
    expect(screen.getByText('Sending...')).toBeInTheDocument();
  });

  it('disables button when sending', () => {
    render(<HelpSupportForm {...defaultProps} sending />);
    expect(screen.getByText('Sending...')).toBeDisabled();
  });

  it('shows sent confirmation', () => {
    render(<HelpSupportForm {...defaultProps} sent />);
    expect(screen.getByText('Message sent.')).toBeInTheDocument();
  });

  it('shows error message', () => {
    render(<HelpSupportForm {...defaultProps} error="Send failed" />);
    expect(screen.getByText('Send failed')).toBeInTheDocument();
  });

  it('renders link to chat', () => {
    render(<HelpSupportForm {...defaultProps} />);
    const link = screen.getByText('Start a guided chat');
    expect(link.closest('a')).toHaveAttribute('href', '/chat');
  });

  it('calls onSubmit on form submit', () => {
    render(<HelpSupportForm {...defaultProps} />);
    fireEvent.click(screen.getByText('Send to Support'));
    expect(defaultProps.onSubmit).toHaveBeenCalled();
  });
});
