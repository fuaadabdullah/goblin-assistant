import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ToastItem } from '../ToastItem';

describe('ToastItem', () => {
  const mockRemove = jest.fn();

  beforeEach(() => {
    mockRemove.mockClear();
  });

  it('renders the toast title', () => {
    render(
      <ToastItem
        toast={{ id: '1', type: 'info', title: 'Hello', message: 'World' }}
        onRemove={mockRemove}
      />
    );
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('renders the toast message when provided', () => {
    render(
      <ToastItem
        toast={{ id: '1', type: 'info', title: 'Hello', message: 'World' }}
        onRemove={mockRemove}
      />
    );
    expect(screen.getByText('World')).toBeInTheDocument();
  });

  it('does not render message when not provided', () => {
    render(<ToastItem toast={{ id: '1', type: 'info', title: 'Hello' }} onRemove={mockRemove} />);
    expect(screen.queryByText('World')).not.toBeInTheDocument();
  });

  it('has role="status" on the container', () => {
    render(<ToastItem toast={{ id: '1', type: 'info', title: 'Hello' }} onRemove={mockRemove} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('sets aria-live to "assertive" for error type', () => {
    render(<ToastItem toast={{ id: '1', type: 'error', title: 'Error' }} onRemove={mockRemove} />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'assertive');
  });

  it('sets aria-live to "assertive" for warning type', () => {
    render(
      <ToastItem toast={{ id: '1', type: 'warning', title: 'Warning' }} onRemove={mockRemove} />
    );
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'assertive');
  });

  it('sets aria-live to "polite" for info type', () => {
    render(<ToastItem toast={{ id: '1', type: 'info', title: 'Info' }} onRemove={mockRemove} />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
  });

  it('sets aria-live to "polite" for success type', () => {
    render(
      <ToastItem toast={{ id: '1', type: 'success', title: 'Success' }} onRemove={mockRemove} />
    );
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
  });

  it('calls onRemove when dismiss button is clicked', () => {
    render(<ToastItem toast={{ id: '1', type: 'info', title: 'Hello' }} onRemove={mockRemove} />);
    fireEvent.click(screen.getByLabelText('Dismiss notification'));
    expect(mockRemove).toHaveBeenCalledWith('1');
  });

  it('has dismiss button with accessible label', () => {
    render(<ToastItem toast={{ id: '1', type: 'info', title: 'Hello' }} onRemove={mockRemove} />);
    expect(screen.getByLabelText('Dismiss notification')).toBeInTheDocument();
  });
});
