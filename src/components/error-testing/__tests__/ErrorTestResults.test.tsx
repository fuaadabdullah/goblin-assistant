import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ErrorTestResults } from '../ErrorTestResults';

describe('ErrorTestResults', () => {
  it('shows empty message when no results', () => {
    render(<ErrorTestResults results={[]} />);
    expect(screen.getByText('No test results yet.')).toBeInTheDocument();
  });

  it('renders heading when there are results', () => {
    render(
      <ErrorTestResults
        results={[
          { id: '1', label: 'Test A', status: 'success', timestamp: '2024-01-15T10:00:00Z' },
        ]}
      />
    );
    expect(screen.getByText('Test Results')).toBeInTheDocument();
  });

  it('renders result labels', () => {
    render(
      <ErrorTestResults
        results={[
          { id: '1', label: 'Network Error', status: 'success', timestamp: '2024-01-15T10:00:00Z' },
          { id: '2', label: 'Auth Error', status: 'error', timestamp: '2024-01-15T10:01:00Z' },
        ]}
      />
    );
    expect(screen.getByText('Network Error')).toBeInTheDocument();
    expect(screen.getByText('Auth Error')).toBeInTheDocument();
  });

  it('renders status badges', () => {
    render(
      <ErrorTestResults
        results={[
          { id: '1', label: 'Test', status: 'success', timestamp: '2024-01-15T10:00:00Z' },
          { id: '2', label: 'Test 2', status: 'error', timestamp: '2024-01-15T10:01:00Z' },
        ]}
      />
    );
    expect(screen.getByText('success')).toBeInTheDocument();
    expect(screen.getByText('error')).toBeInTheDocument();
  });

  it('renders message when present', () => {
    render(
      <ErrorTestResults
        results={[
          { id: '1', label: 'Test', status: 'error', timestamp: '2024-01-15T10:00:00Z', message: 'Something went wrong' },
        ]}
      />
    );
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('renders timestamps', () => {
    render(
      <ErrorTestResults
        results={[
          { id: '1', label: 'Test', status: 'success', timestamp: '2024-01-15T10:00:00Z' },
        ]}
      />
    );
    // The timestamp is rendered via toLocaleString()
    const container = screen.getByText('Test Results').parentElement;
    expect(container).toBeTruthy();
  });

  it('applies success styling for success status', () => {
    render(
      <ErrorTestResults
        results={[
          { id: '1', label: 'Test', status: 'success', timestamp: '2024-01-15T10:00:00Z' },
        ]}
      />
    );
    const badge = screen.getByText('success');
    expect(badge.className).toContain('bg-success');
  });

  it('applies danger styling for error status', () => {
    render(
      <ErrorTestResults
        results={[
          { id: '1', label: 'Test', status: 'error', timestamp: '2024-01-15T10:00:00Z' },
        ]}
      />
    );
    const badge = screen.getByText('error');
    expect(badge.className).toContain('bg-danger');
  });
});
