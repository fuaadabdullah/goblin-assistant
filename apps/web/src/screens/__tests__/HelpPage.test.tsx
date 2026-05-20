import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import HelpPage from '../HelpPage';

jest.mock('@/features/help/HelpScreen', () => function MockHelpScreen() {
  return <div data-testid="help-screen">Help Screen</div>;
});

describe('HelpPage', () => {
  it('renders HelpScreen component', () => {
    render(<HelpPage />);
    expect(screen.getByTestId('help-screen')).toBeInTheDocument();
  });

  it('displays help content', () => {
    render(<HelpPage />);
    expect(screen.getByText('Help Screen')).toBeInTheDocument();
  });

  it('has proper page structure', () => {
    const { container } = render(<HelpPage />);
    expect(container.firstChild).toBeInTheDocument();
  });
});
