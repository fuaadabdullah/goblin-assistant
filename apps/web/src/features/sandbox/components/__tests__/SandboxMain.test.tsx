import React from 'react';
import { render, screen } from '@testing-library/react';

import SandboxMain from '../SandboxMain';

describe('SandboxMain', () => {
  const defaultProps = {
    code: '',
    language: 'python',
    logs: '',
    selectedJob: null,
    onCodeChange: jest.fn(),
  };

  beforeEach(() => jest.clearAllMocks());

  it('renders heading', () => {
    render(<SandboxMain {...defaultProps} />);
    expect(screen.getByText('Safe Experiments')).toBeInTheDocument();
  });

  it('renders subtitle', () => {
    render(<SandboxMain {...defaultProps} />);
    expect(screen.getByText(/automation ideas/)).toBeInTheDocument();
  });

  it('renders code editor textarea', () => {
    render(<SandboxMain {...defaultProps} />);
    expect(screen.getByPlaceholderText(/Enter your python code/)).toBeInTheDocument();
  });

  it('shows correct language in placeholder', () => {
    render(<SandboxMain {...defaultProps} language="javascript" />);
    expect(screen.getByPlaceholderText(/Enter your javascript code/)).toBeInTheDocument();
  });

  it('displays code value in textarea', () => {
    render(<SandboxMain {...defaultProps} code="print(1)" />);
    expect(screen.getByDisplayValue('print(1)')).toBeInTheDocument();
  });

  it('calls onCodeChange when typing', () => {
    render(<SandboxMain {...defaultProps} />);
    const textarea = screen.getByPlaceholderText(/Enter your python code/);
    textarea.focus();
    const event = new Event('change', { bubbles: true });
    Object.defineProperty(event, 'target', { value: { value: 'new code' } });
    textarea.dispatchEvent(event);
  });

  it('shows language label', () => {
    const { container } = render(<SandboxMain {...defaultProps} />);
    const metaDiv = container.querySelector('.text-xs.text-muted');
    expect(metaDiv?.textContent).toContain('python');
  });

  it('shows line count', () => {
    const { container } = render(<SandboxMain {...defaultProps} code={"a\nb\nc"} />);
    const metaDiv = container.querySelector('.text-xs.text-muted');
    expect(metaDiv?.textContent).toContain('3');
  });

  it('shows default output message when no logs', () => {
    render(<SandboxMain {...defaultProps} />);
    expect(screen.getByText('No output yet. Run code to see results.')).toBeInTheDocument();
  });

  it('shows logs when present', () => {
    render(<SandboxMain {...defaultProps} logs="output: 42" />);
    expect(screen.getByText('output: 42')).toBeInTheDocument();
  });

  it('does not show job info when no selected job', () => {
    render(<SandboxMain {...defaultProps} />);
    expect(screen.queryByText(/Job:/)).not.toBeInTheDocument();
  });

  it('shows job ID when job is selected', () => {
    const job = { id: 'abcdefgh-1234', status: 'done' as const, created_at: '2024-01-01' };
    render(<SandboxMain {...defaultProps} selectedJob={job} />);
    expect(screen.getByText('abcdefgh')).toBeInTheDocument();
  });

  it('shows artifacts section for selected job', () => {
    const job = { id: 'j1', status: 'done' as const, created_at: '2024-01-01' };
    render(<SandboxMain {...defaultProps} selectedJob={job} />);
    expect(screen.getByText('Artifacts')).toBeInTheDocument();
  });

  it('does not show guest banner by default', () => {
    render(<SandboxMain {...defaultProps} />);
    expect(screen.queryByText('Guest session')).not.toBeInTheDocument();
  });

  it('shows guest banner when isGuest', () => {
    render(<SandboxMain {...defaultProps} isGuest />);
    expect(screen.getByText('Guest session')).toBeInTheDocument();
    expect(screen.getByText(/temporary/)).toBeInTheDocument();
  });
});
