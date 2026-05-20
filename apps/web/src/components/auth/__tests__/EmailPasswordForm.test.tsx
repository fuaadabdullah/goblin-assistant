import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import EmailPasswordForm from '../EmailPasswordForm';

describe('EmailPasswordForm', () => {
  const mockOnSubmit = jest.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders login form fields', () => {
    render(<EmailPasswordForm onSubmit={mockOnSubmit} isRegister={false} isLoading={false} />);
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('renders register form with Create Account button', () => {
    render(<EmailPasswordForm onSubmit={mockOnSubmit} isRegister={true} isLoading={false} />);
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument();
    expect(screen.getByText(/must be at least 8 characters/i)).toBeInTheDocument();
  });

  it('shows validation error for invalid email', async () => {
    render(<EmailPasswordForm onSubmit={mockOnSubmit} isRegister={false} isLoading={false} />);
    const emailInput = screen.getByLabelText(/email address/i);
    const passwordInput = screen.getByLabelText(/password/i);
    await userEvent.type(emailInput, 'invalid-email');
    await userEvent.type(passwordInput, 'password123');
    fireEvent.submit(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText(/please enter a valid email/i)).toBeInTheDocument();
    });
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('shows validation error for short register password', async () => {
    render(<EmailPasswordForm onSubmit={mockOnSubmit} isRegister={true} isLoading={false} />);
    const emailInput = screen.getByLabelText(/email address/i);
    const passwordInput = screen.getByLabelText(/password/i);
    await userEvent.type(emailInput, 'test@example.com');
    await userEvent.type(passwordInput, 'short');
    fireEvent.submit(screen.getByRole('button', { name: /create account/i }));
    await waitFor(() => {
      expect(screen.getByText(/password must be at least 8 characters/i)).toBeInTheDocument();
    });
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it('shows validation error for empty login password', async () => {
    render(<EmailPasswordForm onSubmit={mockOnSubmit} isRegister={false} isLoading={false} />);
    const emailInput = screen.getByLabelText(/email address/i);
    await userEvent.type(emailInput, 'test@example.com');
    fireEvent.submit(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    });
  });

  it('calls onSubmit with email and password on valid input', async () => {
    render(<EmailPasswordForm onSubmit={mockOnSubmit} isRegister={false} isLoading={false} />);
    const emailInput = screen.getByLabelText(/email address/i);
    const passwordInput = screen.getByLabelText(/password/i);
    await userEvent.type(emailInput, 'test@example.com');
    await userEvent.type(passwordInput, 'password123');
    fireEvent.submit(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith('test@example.com', 'password123');
    });
  });

  it('disables submit button when isLoading is true', () => {
    render(<EmailPasswordForm onSubmit={mockOnSubmit} isRegister={false} isLoading={true} />);
    expect(screen.getByRole('button')).toBeDisabled();
    expect(screen.getByText(/processing/i)).toBeInTheDocument();
  });

  it('clears email error when typing again', async () => {
    render(<EmailPasswordForm onSubmit={mockOnSubmit} isRegister={false} isLoading={false} />);
    fireEvent.submit(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText(/please enter a valid email/i)).toBeInTheDocument();
    });
    await userEvent.type(screen.getByLabelText(/email address/i), 'a');
    expect(screen.queryByText(/please enter a valid email/i)).not.toBeInTheDocument();
  });

  it('clears password error when typing again', async () => {
    render(<EmailPasswordForm onSubmit={mockOnSubmit} isRegister={false} isLoading={false} />);
    const emailInput = screen.getByLabelText(/email address/i);
    await userEvent.type(emailInput, 'test@example.com');
    fireEvent.submit(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => {
      expect(screen.getByText(/password is required/i)).toBeInTheDocument();
    });
    await userEvent.type(screen.getByLabelText(/password/i), 'a');
    expect(screen.queryByText(/password is required/i)).not.toBeInTheDocument();
  });
});
