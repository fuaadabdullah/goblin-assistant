import React from 'react';
import { render, screen } from '@testing-library/react';

import ChatPreviewPanel from '../../features/chat/components/ChatPreviewPanel';

describe('ChatPreviewPanel', () => {
  it('renders the static demo preview and sign-in links', () => {
    render(<ChatPreviewPanel />);

    expect(
      screen.getByText(
        "Hey Goblin, can you summarize last quarter's revenue and flag anything surprising?"
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Sure — here's a quick summary: revenue up 12% YoY, gross margin improved by 3 pts."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText('This preview is static — sign in to continue the conversation.')
    ).toBeInTheDocument();

    const signInLinks = screen.getAllByRole('link', {
      name: 'Sign in to continue this conversation',
    });
    expect(signInLinks).toHaveLength(2);
    expect(signInLinks[0]).toHaveAttribute('href');
    expect(signInLinks[0].getAttribute('href')).toContain('/login?from=%2Fchat%3Fprompt%3D');
    expect(screen.getByRole('link', { name: 'Sign in to Goblin →' })).toHaveAttribute(
      'href',
      '/login'
    );
    expect(screen.getByRole('link', { name: 'Create account' })).toHaveAttribute(
      'href',
      '/login?mode=register'
    );
    expect(screen.getByPlaceholderText('Sign in to continue this conversation...')).toBeDisabled();
  });
});
