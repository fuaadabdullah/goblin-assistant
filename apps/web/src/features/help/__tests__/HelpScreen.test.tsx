import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), prefetch: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/help',
}));

const mockUseSupportForm = vi.fn().mockReturnValue({
  subject: '',
  body: '',
  setSubject: vi.fn(),
  setBody: vi.fn(),
  submit: vi.fn(),
  sending: false,
  sent: false,
  error: null,
});
vi.mock('../hooks/useSupportForm', () => ({
  useSupportForm: () => mockUseSupportForm(),
}));

vi.mock('../components/HelpView', () => ({
  default: function MockHelpView(props: { form: unknown; startupFailure?: unknown }) {
    return (
      <div data-testid="help-view">
        {props.startupFailure ? <span data-testid="startup-failure">failure</span> : null}
      </div>
    );
  },
}));

vi.mock('../../../utils/startup-diagnostics', () => ({
  readStartupDiagnostics: vi.fn(() => ({ status: 'failed' })),
  clearStartupDiagnostics: vi.fn(),
}));

import HelpScreen from '../HelpScreen';

describe('HelpScreen', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders HelpView', () => {
    render(<HelpScreen />);
    expect(screen.getByTestId('help-view')).toBeInTheDocument();
  });

  it('does not show startup failure by default', () => {
    render(<HelpScreen />);
    expect(screen.queryByTestId('startup-failure')).not.toBeInTheDocument();
  });
});
