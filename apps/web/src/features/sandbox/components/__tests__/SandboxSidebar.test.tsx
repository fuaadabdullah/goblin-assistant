import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('next/link', () => function MockLink({ children, href, onClick, ...rest }: { children: React.ReactNode; href: string; onClick?: () => void; [key: string]: unknown }) {
  return <a href={href} onClick={onClick} {...rest}>{children}</a>;
});

jest.mock('lucide-react', () => new Proxy({}, {
  get: (_, name) => {
    if (name === '__esModule') return true;
    return (props: Record<string, unknown>) => <span data-testid={`icon-${String(name)}`} {...props} />;
  },
}));

import SandboxSidebar from '../SandboxSidebar';
import type { SandboxJob } from '../../types';

const mockJobs: SandboxJob[] = [
  { id: 'job-12345678', status: 'completed', created_at: '2024-01-01T00:00:00Z', language: 'python', code: 'print(1)' } as SandboxJob,
  { id: 'job-87654321', status: 'failed', created_at: '2024-01-02T00:00:00Z', language: 'python', code: 'x' } as SandboxJob,
];

describe('SandboxSidebar', () => {
  const defaultProps = {
    language: 'python',
    loading: false,
    code: 'print("hello")',
    jobs: mockJobs,
    selectedJobId: undefined,
    onLanguageChange: jest.fn(),
    onRun: jest.fn(),
    onClear: jest.fn(),
    onRefresh: jest.fn(),
    onSelectJob: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders title and description', () => {
    render(<SandboxSidebar {...defaultProps} />);
    expect(screen.getByText('Sandbox')).toBeInTheDocument();
    expect(screen.getByText(/try experimental features/i)).toBeInTheDocument();
  });

  it('renders language selector', () => {
    render(<SandboxSidebar {...defaultProps} />);
    const select = screen.getByLabelText(/language/i);
    expect(select).toHaveValue('python');
  });

  it('calls onRun when Run Code is clicked', () => {
    render(<SandboxSidebar {...defaultProps} />);
    fireEvent.click(screen.getByText(/Run Code/));
    expect(defaultProps.onRun).toHaveBeenCalled();
  });

  it('disables Run when code is empty', () => {
    render(<SandboxSidebar {...defaultProps} code="" />);
    const runBtn = screen.getByText(/Run Code/).closest('button');
    expect(runBtn).toBeDisabled();
  });

  it('disables Run when loading', () => {
    render(<SandboxSidebar {...defaultProps} loading={true} />);
    expect(screen.getByText(/Running.../)).toBeInTheDocument();
  });

  it('calls onClear when Clear is clicked', () => {
    render(<SandboxSidebar {...defaultProps} />);
    fireEvent.click(screen.getByText(/Clear/));
    expect(defaultProps.onClear).toHaveBeenCalled();
  });

  it('calls onRefresh when Refresh Jobs is clicked', () => {
    render(<SandboxSidebar {...defaultProps} />);
    fireEvent.click(screen.getByText(/Refresh Jobs/));
    expect(defaultProps.onRefresh).toHaveBeenCalled();
  });

  it('renders job list', () => {
    render(<SandboxSidebar {...defaultProps} />);
    expect(screen.getByText('job-1234')).toBeInTheDocument();
    expect(screen.getByText('completed')).toBeInTheDocument();
    expect(screen.getByText('failed')).toBeInTheDocument();
  });

  it('calls onSelectJob when a job is clicked', () => {
    render(<SandboxSidebar {...defaultProps} />);
    fireEvent.click(screen.getByText('job-1234'));
    expect(defaultProps.onSelectJob).toHaveBeenCalledWith(mockJobs[0]);
  });

  it('highlights selected job', () => {
    render(<SandboxSidebar {...defaultProps} selectedJobId="job-12345678" />);
    const jobButton = screen.getByText('job-1234').closest('button');
    expect(jobButton?.className).toContain('bg-primary');
  });

  it('shows empty message when no jobs', () => {
    render(<SandboxSidebar {...defaultProps} jobs={[]} />);
    expect(screen.getByText('No jobs yet')).toBeInTheDocument();
  });

  it('shows guest message when isGuest', () => {
    render(<SandboxSidebar {...defaultProps} isGuest={true} />);
    expect(screen.getByText(/sign in to view/i)).toBeInTheDocument();
  });

  it('calls onLanguageChange when selection changes', () => {
    render(<SandboxSidebar {...defaultProps} />);
    fireEvent.change(screen.getByLabelText(/language/i), { target: { value: 'python' } });
    expect(defaultProps.onLanguageChange).toHaveBeenCalledWith('python');
  });
});
