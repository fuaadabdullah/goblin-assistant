import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import HelpTopics from '../HelpTopics';

describe('HelpTopics', () => {
  const topics = [
    { title: 'Getting Started', body: 'How to begin using the app.' },
    { title: 'API Keys', body: 'Set up provider API keys.' },
  ];

  it('renders the section heading', () => {
    render(<HelpTopics topics={topics} />);
    expect(screen.getByText('Common Topics')).toBeInTheDocument();
  });

  it('renders all topic titles', () => {
    render(<HelpTopics topics={topics} />);
    expect(screen.getByText('Getting Started')).toBeInTheDocument();
    expect(screen.getByText('API Keys')).toBeInTheDocument();
  });

  it('renders all topic bodies', () => {
    render(<HelpTopics topics={topics} />);
    expect(screen.getByText('How to begin using the app.')).toBeInTheDocument();
    expect(screen.getByText('Set up provider API keys.')).toBeInTheDocument();
  });

  it('renders nothing for empty array', () => {
    render(<HelpTopics topics={[]} />);
    expect(screen.getByText('Common Topics')).toBeInTheDocument();
  });
});
