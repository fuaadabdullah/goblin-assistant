import React from 'react';
import { render, screen } from '@testing-library/react';

import GoblinBootScreen from '../GoblinBootScreen';

jest.mock('../StatusLine', () =>
  function MockStatusLine({ label, state }: { label: string; state: string }) {
    return <div data-testid={`status-${state}`}>{label}</div>;
  }
);

jest.mock('../GoblinLoader', () =>
  function MockGoblinLoader() {
    return <div data-testid="goblin-loader" />;
  }
);

describe('GoblinBootScreen', () => {
  it('renders heading', () => {
    render(<GoblinBootScreen status="checking-auth" message="Starting..." />);
    expect(screen.getByText('Initializing gateway')).toBeInTheDocument();
  });

  it('renders status message', () => {
    render(<GoblinBootScreen status="checking-auth" message="Authenticating user" />);
    expect(screen.getByText('Authenticating user')).toBeInTheDocument();
  });

  it('renders Goblin Assistant label', () => {
    render(<GoblinBootScreen status="checking-auth" message="test" />);
    expect(screen.getByText('Goblin Assistant')).toBeInTheDocument();
  });

  it('renders goblin loader', () => {
    render(<GoblinBootScreen status="checking-auth" message="test" />);
    expect(screen.getByTestId('goblin-loader')).toBeInTheDocument();
  });

  it('renders all four steps', () => {
    render(<GoblinBootScreen status="checking-auth" message="test" />);
    expect(screen.getByText('Checking authentication')).toBeInTheDocument();
    expect(screen.getByText('Loading configuration')).toBeInTheDocument();
    expect(screen.getByText('Initializing runtime')).toBeInTheDocument();
    expect(screen.getByText('Ready to launch')).toBeInTheDocument();
  });

  it('marks first step active when checking-auth', () => {
    render(<GoblinBootScreen status="checking-auth" message="test" />);
    expect(screen.getByTestId('status-active')).toHaveTextContent('Checking authentication');
  });

  it('marks first step complete when loading-config', () => {
    render(<GoblinBootScreen status="loading-config" message="test" />);
    const completes = screen.getAllByTestId('status-complete');
    expect(completes[0]).toHaveTextContent('Checking authentication');
  });

  it('marks current step active when loading-config', () => {
    render(<GoblinBootScreen status="loading-config" message="test" />);
    expect(screen.getByTestId('status-active')).toHaveTextContent('Loading configuration');
  });

  it('shows status update label', () => {
    render(<GoblinBootScreen status="ready" message="All systems go" />);
    expect(screen.getByText('Status update')).toBeInTheDocument();
    expect(screen.getByText('All systems go')).toBeInTheDocument();
  });

  it('sets error state on all steps when status is error', () => {
    render(<GoblinBootScreen status="error" message="Startup failed" />);
    const errors = screen.getAllByTestId('status-error');
    expect(errors.length).toBe(4);
  });
});
