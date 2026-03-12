import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

import AccountProfileForm from '../AccountProfileForm';

describe('AccountProfileForm', () => {
  const defaultProps = {
    name: 'Test User',
    email: 'test@example.com',
    saved: false,
    onNameChange: jest.fn(),
    onSave: jest.fn(),
  };

  beforeEach(() => jest.clearAllMocks());

  it('renders profile heading', () => {
    render(<AccountProfileForm {...defaultProps} />);
    expect(screen.getByText('Profile')).toBeInTheDocument();
  });

  it('renders name input with value', () => {
    render(<AccountProfileForm {...defaultProps} />);
    expect(screen.getByLabelText('Full name')).toHaveValue('Test User');
  });

  it('renders email input disabled', () => {
    render(<AccountProfileForm {...defaultProps} />);
    const emailInput = screen.getByLabelText('Email');
    expect(emailInput).toHaveValue('test@example.com');
    expect(emailInput).toBeDisabled();
  });

  it('calls onNameChange when name typed', () => {
    render(<AccountProfileForm {...defaultProps} />);
    fireEvent.change(screen.getByLabelText('Full name'), { target: { value: 'New Name' } });
    expect(defaultProps.onNameChange).toHaveBeenCalledWith('New Name');
  });

  it('calls onSave on form submit', () => {
    render(<AccountProfileForm {...defaultProps} />);
    fireEvent.submit(screen.getByText('Save Changes').closest('form')!);
    expect(defaultProps.onSave).toHaveBeenCalled();
  });

  it('shows Save Changes button text by default', () => {
    render(<AccountProfileForm {...defaultProps} />);
    expect(screen.getByText('Save Changes')).toBeInTheDocument();
  });

  it('shows Saving... when saving is true', () => {
    render(<AccountProfileForm {...defaultProps} saving />);
    expect(screen.getByText('Saving...')).toBeInTheDocument();
  });

  it('disables submit button when saving', () => {
    render(<AccountProfileForm {...defaultProps} saving />);
    expect(screen.getByText('Saving...')).toBeDisabled();
  });

  it('shows Saved message when saved is true', () => {
    render(<AccountProfileForm {...defaultProps} saved />);
    expect(screen.getByText('Saved.')).toBeInTheDocument();
  });

  it('shows error when error prop provided', () => {
    render(<AccountProfileForm {...defaultProps} error="Save failed" />);
    expect(screen.getByText('Save failed')).toBeInTheDocument();
  });

  it('does not show error when error is null', () => {
    render(<AccountProfileForm {...defaultProps} error={null} />);
    expect(screen.queryByText('Save failed')).not.toBeInTheDocument();
  });
});
