import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

import MessageActions from '../MessageActions';

describe('MessageActions', () => {
  const defaultProps = { role: 'user' as const, onCopy: vi.fn() };

  beforeEach(() => vi.clearAllMocks());

  it('renders copy button', () => {
    render(<MessageActions {...defaultProps} />);
    expect(screen.getByLabelText('Copy message content')).toBeInTheDocument();
  });

  it('calls onCopy when copy clicked', () => {
    render(<MessageActions {...defaultProps} />);
    fireEvent.click(screen.getByLabelText('Copy message content'));
    expect(defaultProps.onCopy).toHaveBeenCalled();
  });

  it('does not show regenerate for user messages', () => {
    render(<MessageActions {...defaultProps} onRegenerate={vi.fn()} />);
    expect(screen.queryByLabelText('Regenerate response')).not.toBeInTheDocument();
  });

  it('shows regenerate for assistant messages', () => {
    render(<MessageActions {...defaultProps} role="assistant" onRegenerate={vi.fn()} />);
    expect(screen.getByLabelText('Regenerate response')).toBeInTheDocument();
  });

  it('calls onRegenerate when clicked', () => {
    const onRegenerate = vi.fn();
    render(<MessageActions {...defaultProps} role="assistant" onRegenerate={onRegenerate} />);
    fireEvent.click(screen.getByLabelText('Regenerate response'));
    expect(onRegenerate).toHaveBeenCalled();
  });

  it('hides regenerate when showRegenerate is false', () => {
    render(
      <MessageActions
        {...defaultProps}
        role="assistant"
        onRegenerate={vi.fn()}
        showRegenerate={false}
      />
    );
    expect(screen.queryByLabelText('Regenerate response')).not.toBeInTheDocument();
  });

  it('shows delete button', () => {
    render(<MessageActions {...defaultProps} onDelete={vi.fn()} />);
    expect(screen.getByLabelText('Delete message')).toBeInTheDocument();
  });

  it('calls onDelete when clicked', () => {
    const onDelete = vi.fn();
    render(<MessageActions {...defaultProps} onDelete={onDelete} />);
    fireEvent.click(screen.getByLabelText('Delete message'));
    expect(onDelete).toHaveBeenCalled();
  });

  it('hides delete when showDelete is false', () => {
    render(<MessageActions {...defaultProps} onDelete={vi.fn()} showDelete={false} />);
    expect(screen.queryByLabelText('Delete message')).not.toBeInTheDocument();
  });

  it('hides delete when onDelete is not provided', () => {
    render(<MessageActions {...defaultProps} />);
    expect(screen.queryByLabelText('Delete message')).not.toBeInTheDocument();
  });
});
