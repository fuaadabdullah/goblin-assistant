import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('@/features/agent/AgentScreen', () => ({
  default: function MockAgentScreen() {
    return <div data-testid="agent-screen">Agent Screen</div>;
  },
}));

import AgentPage from '../AgentPage';

describe('AgentPage', () => {
  it('renders the agent screen', () => {
    render(<AgentPage />);
    expect(screen.getByTestId('agent-screen')).toBeInTheDocument();
  });
});
