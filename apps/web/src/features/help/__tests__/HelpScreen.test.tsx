import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

const mockPush = jest.fn();
let mockSearchParams = new URLSearchParams();
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => mockSearchParams,
}));

const mockUseSupportForm = jest.fn().mockReturnValue({
  subject: '',
  body: '',
  setSubject: jest.fn(),
  setBody: jest.fn(),
  submit: jest.fn(),
  sending: false,
  sent: false,
  error: null,
});
jest.mock('../hooks/useSupportForm', () => ({
  useSupportForm: () => mockUseSupportForm(),
}));

jest.mock('../components/HelpView', () => {
  return function MockHelpView(props: { form: unknown; startupFailure?: unknown }) {
    return (
      <div data-testid="help-view">
        {props.startupFailure ? <span data-testid="startup-failure">failure</span> : null}
      </div>
    );
  };
});

jest.mock('../../../utils/startup-diagnostics', () => ({
  readStartupDiagnostics: jest.fn(() => ({ status: 'failed' })),
  clearStartupDiagnostics: jest.fn(),
}));

import HelpScreen from '../HelpScreen';

describe('HelpScreen', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders HelpView', () => {
    render(<HelpScreen />);
    expect(screen.getByTestId('help-view')).toBeInTheDocument();
  });

  it('does not show startup failure by default', () => {
    render(<HelpScreen />);
    expect(screen.queryByTestId('startup-failure')).not.toBeInTheDocument();
  });
});
