import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import ChatComposer from '../ChatComposer';

// Mock dependencies
jest.mock('next/link', () => {
  return function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
    return <a href={href}>{children}</a>;
  };
});
jest.mock('lucide-react', () => ({
  Loader2: (props: Record<string, unknown>) => <span data-testid="loader" {...props} />,
  Paperclip: (props: Record<string, unknown>) => <span data-testid="paperclip" {...props} />,
  X: (props: Record<string, unknown>) => <span data-testid="x-icon" {...props} />,
}));
jest.mock('../AuthRequired', () => ({
  AuthRequired: () => <div data-testid="auth-required">Auth Required</div>,
}));
jest.mock('@/utils/format-cost', () => ({
  formatCost: (val: number) => `$${val.toFixed(4)}`,
}));
jest.mock('../../../../content/brand', () => ({
  CHAT_COMPOSER_PLACEHOLDER: 'Type a message...',
  CHAT_COMPOSER_TIP: 'Press Enter to send',
}));

import type { RefObject } from 'react';
import { createRef } from 'react';

const defaultProps = {
  input: '',
  inputRef: createRef<HTMLTextAreaElement>() as RefObject<HTMLTextAreaElement>,
  isSending: false,
  quickPrompts: [
    { label: 'Prompt 1', prompt: 'Hello' },
    { label: 'Prompt 2', prompt: 'World' },
    { label: 'Prompt 3', prompt: 'Test' },
    { label: 'Prompt 4', prompt: 'Extra' },
  ],
  onInputChange: jest.fn(),
  onClear: jest.fn(),
  onSend: jest.fn(),
  onKeyDown: jest.fn(),
  onPromptClick: jest.fn(),
};

describe('ChatComposer', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders textarea with placeholder', () => {
    render(<ChatComposer {...defaultProps} />);
    expect(screen.getByLabelText('Chat message input')).toBeInTheDocument();
  });

  it('displays provider and model info', () => {
    render(<ChatComposer {...defaultProps} selectedProvider="openai" selectedModel="gpt-4" />);
    expect(screen.getByText('openai')).toBeInTheDocument();
    expect(screen.getByText('gpt-4')).toBeInTheDocument();
  });

  it('shows "auto" when no provider/model selected', () => {
    render(<ChatComposer {...defaultProps} />);
    const autoTexts = screen.getAllByText('auto');
    expect(autoTexts.length).toBeGreaterThanOrEqual(2);
  });

  it('calls onInputChange when text is typed', () => {
    render(<ChatComposer {...defaultProps} />);
    const textarea = screen.getByLabelText('Chat message input');
    fireEvent.change(textarea, { target: { value: 'Hello' } });
    expect(defaultProps.onInputChange).toHaveBeenCalledWith('Hello');
  });

  it('calls onSend when send button is clicked', () => {
    render(<ChatComposer {...defaultProps} input="Some text" />);
    const sendBtn = screen.getByLabelText('Send message');
    fireEvent.click(sendBtn);
    expect(defaultProps.onSend).toHaveBeenCalled();
  });

  it('disables send button when input is empty', () => {
    render(<ChatComposer {...defaultProps} input="" />);
    const sendBtn = screen.getByLabelText('Send message');
    expect(sendBtn).toBeDisabled();
  });

  it('disables send button when sending', () => {
    render(<ChatComposer {...defaultProps} input="text" isSending />);
    const sendBtn = screen.getByRole('button', { name: /send/i });
    expect(sendBtn).toBeDisabled();
  });

  it('shows "Sending…" text when sending', () => {
    render(<ChatComposer {...defaultProps} input="text" isSending />);
    expect(screen.getByText('Sending…')).toBeInTheDocument();
  });

  it('calls onClear when clear button is clicked', () => {
    render(<ChatComposer {...defaultProps} />);
    fireEvent.click(screen.getByText('Clear'));
    expect(defaultProps.onClear).toHaveBeenCalled();
  });

  it('renders max 3 quick prompts', () => {
    render(<ChatComposer {...defaultProps} />);
    expect(screen.getByText('Prompt 1')).toBeInTheDocument();
    expect(screen.getByText('Prompt 2')).toBeInTheDocument();
    expect(screen.getByText('Prompt 3')).toBeInTheDocument();
    expect(screen.queryByText('Prompt 4')).not.toBeInTheDocument();
  });

  it('calls onPromptClick when a quick prompt is clicked', () => {
    render(<ChatComposer {...defaultProps} />);
    fireEvent.click(screen.getByText('Prompt 1'));
    expect(defaultProps.onPromptClick).toHaveBeenCalledWith('Hello');
  });

  it('shows character counter when over 9000 chars', () => {
    const longInput = 'a'.repeat(9001);
    render(<ChatComposer {...defaultProps} input={longInput} />);
    expect(screen.getByText(/9,001/)).toBeInTheDocument();
  });

  it('does not show character counter under 9000 chars', () => {
    render(<ChatComposer {...defaultProps} input="short" />);
    expect(screen.queryByText(/10,000/)).not.toBeInTheDocument();
  });

  it('shows AuthRequired when authError is true', () => {
    render(<ChatComposer {...defaultProps} authError />);
    expect(screen.getByTestId('auth-required')).toBeInTheDocument();
  });

  it('does not show AuthRequired when authError is false', () => {
    render(<ChatComposer {...defaultProps} authError={false} />);
    expect(screen.queryByTestId('auth-required')).not.toBeInTheDocument();
  });

  it('renders file upload button', () => {
    render(<ChatComposer {...defaultProps} />);
    expect(screen.getByLabelText('Attach file')).toBeInTheDocument();
  });

  it('renders pending attachments', () => {
    const attachments = [
      { file_id: 'f1', filename: 'doc.pdf', mime_type: 'application/pdf', size_bytes: 1024 },
    ];
    render(<ChatComposer {...defaultProps} pendingAttachments={attachments} />);
    expect(screen.getByText('doc.pdf')).toBeInTheDocument();
  });

  it('calls onRemoveAttachment when remove button clicked', () => {
    const onRemove = jest.fn();
    const attachments = [
      { file_id: 'f1', filename: 'doc.pdf', mime_type: 'application/pdf', size_bytes: 1024 },
    ];
    render(<ChatComposer {...defaultProps} pendingAttachments={attachments} onRemoveAttachment={onRemove} />);
    fireEvent.click(screen.getByLabelText('Remove doc.pdf'));
    expect(onRemove).toHaveBeenCalledWith('f1');
  });

  it('shows uploading indicator', () => {
    render(<ChatComposer {...defaultProps} isUploading pendingAttachments={[]} />);
    expect(screen.getByText('Uploading…')).toBeInTheDocument();
  });

  it('displays cost estimates', () => {
    render(<ChatComposer {...defaultProps} estimatedTokens={500} estimatedCostUsd={0.01} totalTokens={1000} totalCostUsd={0.05} />);
    expect(screen.getByText('~500')).toBeInTheDocument();
    expect(screen.getByText('1000')).toBeInTheDocument();
  });

  it('shows settings link', () => {
    render(<ChatComposer {...defaultProps} />);
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('disables textarea when sending', () => {
    render(<ChatComposer {...defaultProps} isSending />);
    expect(screen.getByLabelText('Chat message input')).toBeDisabled();
  });
});
