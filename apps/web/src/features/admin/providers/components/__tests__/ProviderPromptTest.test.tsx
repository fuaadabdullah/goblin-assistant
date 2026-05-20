import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

jest.mock('../../../../../components/ui', () => ({
  Button: ({ children, onClick, disabled }: { children: React.ReactNode; onClick: () => void; disabled?: boolean }) =>
    <button onClick={onClick} disabled={disabled}>{children}</button>,
}));

import ProviderPromptTest from '../ProviderPromptTest';

const defaultProps = {
  prompt: 'Test prompt',
  onPromptChange: jest.fn(),
  onTest: jest.fn(),
  isTesting: false,
  disabled: false,
};

describe('ProviderPromptTest', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders heading', () => {
    render(<ProviderPromptTest {...defaultProps} />);
    expect(screen.getByText('Test with Custom Prompt')).toBeInTheDocument();
  });

  it('renders textarea with prompt value', () => {
    render(<ProviderPromptTest {...defaultProps} />);
    expect(screen.getByLabelText(/test prompt/i)).toHaveValue('Test prompt');
  });

  it('calls onPromptChange on textarea change', () => {
    render(<ProviderPromptTest {...defaultProps} />);
    fireEvent.change(screen.getByLabelText(/test prompt/i), { target: { value: 'New prompt' } });
    expect(defaultProps.onPromptChange).toHaveBeenCalledWith('New prompt');
  });

  it('renders test button', () => {
    render(<ProviderPromptTest {...defaultProps} />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('shows Test API with Prompt text when not testing', () => {
    render(<ProviderPromptTest {...defaultProps} />);
    expect(screen.getByText('Test API with Prompt')).toBeInTheDocument();
  });

  it('shows Testing with prompt text when testing', () => {
    render(<ProviderPromptTest {...defaultProps} isTesting />);
    expect(screen.getByText('Testing with prompt...')).toBeInTheDocument();
  });

  it('calls onTest on button click', () => {
    render(<ProviderPromptTest {...defaultProps} />);
    fireEvent.click(screen.getByRole('button'));
    expect(defaultProps.onTest).toHaveBeenCalled();
  });

  it('disables button when prompt is empty', () => {
    render(<ProviderPromptTest {...defaultProps} prompt="" />);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('disables button when disabled prop is true', () => {
    render(<ProviderPromptTest {...defaultProps} disabled />);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('has placeholder text', () => {
    render(<ProviderPromptTest {...defaultProps} prompt="" />);
    expect(screen.getByPlaceholderText(/hello world/i)).toBeInTheDocument();
  });
});
