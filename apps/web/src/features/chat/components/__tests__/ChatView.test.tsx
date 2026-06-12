import { render, screen, fireEvent } from '@testing-library/react';

// Mock all child components
vi.mock('../ChatHeader', () => ({
  default: function MockChatHeader(props: Record<string, unknown>) {
    return (
      <div data-testid="chat-header">
        <button onClick={props.onToggleMobilePanel as () => void}>Toggle Panel</button>
        <span data-testid="active-mobile-tab">{props.activeMobilePanelTab as string}</span>
      </div>
    );
  },
}));
vi.mock('../ChatMessageList', () => ({
  default: function MockChatMessageList() {
    return <div data-testid="chat-message-list" />;
  },
}));
vi.mock('../ChatComposer', () => ({
  default: function MockChatComposer() {
    return <div data-testid="chat-composer" />;
  },
}));
vi.mock('../ChatSidebar', () => ({
  default: function MockChatSidebar(props: Record<string, unknown>) {
    return (
      <div data-testid="chat-sidebar" className={props.className as string}>
        <button onClick={() => (props.onSelectThread as (k: string) => void)('thread-1')}>
          Select Thread
        </button>
        <button onClick={props.onNewConversation as () => void}>New Conv</button>
      </div>
    );
  },
}));
vi.mock('../../../../components/Seo', () => ({
  default: function MockSeo(props: Record<string, unknown>) {
    return <div data-testid="seo" data-title={props.title} />;
  },
}));
// AuthPrompt is no longer used by ChatView - it shows an inline login UI instead
// vi.mock('../../../../components/auth/AuthPrompt', ...)

vi.mock('../ChatPreviewPanel', () => ({
  default: function MockChatPreviewPanel() {
    return <div data-testid="chat-preview-panel" />;
  },
}));
vi.mock('next/link', () => ({
  default: function MockLink(props: Record<string, unknown>) {
    const href =
      typeof props.href === 'object' && props.href !== null
        ? (props.href as { pathname: string }).pathname
        : String(props.href);
    return (
      <a href={href} className={props.className as string}>
        {props.children as React.ReactNode}
      </a>
    );
  },
}));
vi.mock('../../../../components/ui/input', () => ({
  Input: function MockInput(props: Record<string, unknown>) {
    return <input {...(props as object)} />;
  },
}));

const mockIsAuthenticated = vi.fn().mockReturnValue(true);
vi.mock('../../../../hooks/api/useAuthSession', () => ({
  useAuthSession: () => ({ isAuthenticated: mockIsAuthenticated() }),
}));

const mockChatSidebarOpen = vi.fn().mockReturnValue(false);
const mockSetChatSidebarOpen = vi.fn();
vi.mock('../../../../store/uiStore', () => ({
  useUIStore: (selector: (state: Record<string, unknown>) => unknown) => {
    const state = {
      chatSidebarOpen: mockChatSidebarOpen(),
      setChatSidebarOpen: mockSetChatSidebarOpen,
    };
    return selector(state);
  },
}));
vi.mock('../../../../hooks/useFocusTrap', () => ({
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
  setInput: vi.fn(),
  sendMessage: vi.fn(),
  selectThread: vi.fn(),
  handleClearChat: vi.fn(),
  handlePromptClick: vi.fn(),
  handleKeyDown: vi.fn(),
  selectedProvider: 'openai',
  selectedModel: 'gpt-4',
  inputEstimate: null,
  isMessagesLoading: false,
  deleteMessage: vi.fn(),
  copyMessage: vi.fn(),
  regenerateMessage: vi.fn(),
  pendingAttachments: [],
  isUploading: false,
  handleFileSelected: vi.fn(),
  removePendingAttachment: vi.fn(),
};

describe('ChatView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated.mockReturnValue(true);
    mockChatSidebarOpen.mockReturnValue(false);
  });

  it('renders chat UI when authenticated', () => {
    render(<ChatView session={mockSession as never} isAdmin={false} />);
    expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    expect(screen.getByTestId('chat-message-list')).toBeInTheDocument();
    expect(screen.getByTestId('chat-composer')).toBeInTheDocument();
  });

  it('shows inline login UI when not authenticated', () => {
    mockIsAuthenticated.mockReturnValue(false);
    render(<ChatView session={mockSession as never} isAdmin={false} />);
    // Component now renders inline login/preview UI instead of AuthPrompt
    expect(screen.getByText('Sign in to Goblin →')).toBeInTheDocument();
    expect(screen.queryByTestId('chat-composer')).not.toBeInTheDocument();
  });

  it('renders Seo component with correct title', () => {
    render(<ChatView session={mockSession as never} isAdmin={false} />);
    expect(screen.getByTestId('seo')).toHaveAttribute('data-title', 'Chat');
  });

  it('renders sidebars (unified mobile panel + desktop)', () => {
    render(<ChatView session={mockSession as never} isAdmin={false} />);
    const sidebars = screen.getAllByTestId('chat-sidebar');
    expect(sidebars.length).toBe(2);
    expect(screen.getByRole('dialog', { name: 'Chat mobile panel' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Conversations' })).toHaveAttribute(
      'aria-selected',
      'true'
    );
    expect(screen.getAllByLabelText('Close chat panel')).toHaveLength(1);
  });

  it('switches unified mobile panel tabs', () => {
    render(<ChatView session={mockSession as never} isAdmin={false} />);
    fireEvent.click(screen.getByRole('tab', { name: 'Preview' }));
    expect(screen.getByRole('tab', { name: 'Preview' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByTestId('chat-preview-panel')).toBeInTheDocument();
    expect(screen.getByTestId('active-mobile-tab')).toHaveTextContent('preview');
  });

  it('opens unified mobile panel through header toggle', () => {
    render(<ChatView session={mockSession as never} isAdmin={false} />);
    fireEvent.click(screen.getByText('Toggle Panel'));
    expect(mockSetChatSidebarOpen).toHaveBeenCalledWith(true);
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
