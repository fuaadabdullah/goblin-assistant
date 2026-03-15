import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock all child components
jest.mock('../ChatHeader', () => {
  return function MockChatHeader(props: Record<string, unknown>) {
    return <div data-testid="chat-header"><button onClick={props.onToggleSidebar as () => void}>Toggle</button></div>;
  };
});
jest.mock('../ChatMessageList', () => {
  return function MockChatMessageList() {
    return <div data-testid="chat-message-list" />;
  };
});
jest.mock('../ChatComposer', () => {
  return function MockChatComposer() {
    return <div data-testid="chat-composer" />;
  };
});
jest.mock('../ChatSidebar', () => {
  return function MockChatSidebar(props: Record<string, unknown>) {
    return (
      <div data-testid="chat-sidebar" className={props.className as string}>
        <button onClick={() => (props.onSelectThread as (k: string) => void)('thread-1')}>Select Thread</button>
        <button onClick={props.onNewConversation as () => void}>New Conv</button>
      </div>
    );
  };
});
jest.mock('../../../../components/Seo', () => {
  return function MockSeo(props: Record<string, unknown>) {
    return <div data-testid="seo" data-title={props.title} />;
  };
});
jest.mock('../../../../components/auth/AuthPrompt', () => {
  return function MockAuthPrompt() {
    return <div data-testid="auth-prompt" />;
  };
});

const mockIsAuthenticated = jest.fn().mockReturnValue(true);
jest.mock('../../../../hooks/api/useAuthSession', () => ({
  useAuthSession: () => ({ isAuthenticated: mockIsAuthenticated() }),
}));

const mockChatSidebarOpen = jest.fn().mockReturnValue(false);
const mockToggleChatSidebar = jest.fn();
const mockSetChatSidebarOpen = jest.fn();
jest.mock('../../../../store/uiStore', () => ({
  useUIStore: (selector: (state: Record<string, unknown>) => unknown) => {
    const state = {
      chatSidebarOpen: mockChatSidebarOpen(),
      toggleChatSidebar: mockToggleChatSidebar,
      setChatSidebarOpen: mockSetChatSidebarOpen,
    };
    return selector(state);
  },
}));
jest.mock('../../../../hooks/useFocusTrap', () => ({
  useFocusTrap: () => ({ current: null }),
}));

import ChatView from '../ChatView';
import { createRef } from 'react';

const mockSession = {
  messages: [],
  input: '',
  isSending: false,
  totalTokens: 0,
  totalCostUsd: 0,
  quickPrompts: [],
  threads: [],
  isThreadsLoading: false,
  activeThreadKey: null,
  inputRef: createRef<HTMLTextAreaElement>(),
  bottomRef: createRef<HTMLDivElement>(),
  authError: false,
  setInput: jest.fn(),
  sendMessage: jest.fn(),
  selectThread: jest.fn(),
  handleClearChat: jest.fn(),
  handlePromptClick: jest.fn(),
  handleKeyDown: jest.fn(),
  selectedProvider: 'openai',
  selectedModel: 'gpt-4',
  inputEstimate: null,
  isMessagesLoading: false,
  deleteMessage: jest.fn(),
  copyMessage: jest.fn(),
  regenerateMessage: jest.fn(),
  pendingAttachments: [],
  isUploading: false,
  handleFileSelected: jest.fn(),
  removePendingAttachment: jest.fn(),
};

describe('ChatView', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockIsAuthenticated.mockReturnValue(true);
    mockChatSidebarOpen.mockReturnValue(false);
  });

  it('renders chat UI when authenticated', () => {
    render(<ChatView session={mockSession as never} isAdmin={false} />);
    expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    expect(screen.getByTestId('chat-message-list')).toBeInTheDocument();
    expect(screen.getByTestId('chat-composer')).toBeInTheDocument();
  });

  it('shows AuthPrompt when not authenticated', () => {
    mockIsAuthenticated.mockReturnValue(false);
    render(<ChatView session={mockSession as never} isAdmin={false} />);
    expect(screen.getByTestId('auth-prompt')).toBeInTheDocument();
    expect(screen.queryByTestId('chat-composer')).not.toBeInTheDocument();
  });

  it('renders Seo component with correct title', () => {
    render(<ChatView session={mockSession as never} isAdmin={false} />);
    expect(screen.getByTestId('seo')).toHaveAttribute('data-title', 'Chat');
  });

  it('renders sidebars (mobile + desktop)', () => {
    render(<ChatView session={mockSession as never} isAdmin={false} />);
    const sidebars = screen.getAllByTestId('chat-sidebar');
    expect(sidebars.length).toBe(2); // mobile + desktop
  });

  it('closes sidebar on thread select', () => {
    render(<ChatView session={mockSession as never} isAdmin={false} />);
    const selectBtns = screen.getAllByText('Select Thread');
    fireEvent.click(selectBtns[0]);
    expect(mockSession.selectThread).toHaveBeenCalledWith('thread-1');
    expect(mockSetChatSidebarOpen).toHaveBeenCalledWith(false);
  });

  it('closes sidebar on new conversation', () => {
    render(<ChatView session={mockSession as never} isAdmin={false} />);
    const newBtns = screen.getAllByText('New Conv');
    fireEvent.click(newBtns[0]);
    expect(mockSession.handleClearChat).toHaveBeenCalled();
    expect(mockSetChatSidebarOpen).toHaveBeenCalledWith(false);
  });

  it('shows sign-in Seo title when not authenticated', () => {
    mockIsAuthenticated.mockReturnValue(false);
    render(<ChatView session={mockSession as never} isAdmin={false} />);
    expect(screen.getByTestId('seo')).toHaveAttribute('data-title', 'Chat - Sign In Required');
  });
});
