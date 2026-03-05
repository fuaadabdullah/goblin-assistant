"use client";

import React, { useState, useRef, useEffect } from 'react';
import { ArrowUp, User, Loader, Star, MessageSquare, Copy, RotateCcw, CheckCircle, AlertCircle, Code } from 'lucide-react';
import { Button } from '@/components/ui';
import { Badge } from '@/components/ui/Badge';
import { useTranslation } from '@/i18n';
import { LanguageSwitcher } from '@/components/LanguageSwitcher';
import { Sandbox } from '@/components/Sandbox';
import toast, { Toaster } from 'react-hot-toast';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
}

// For localStorage deserialization (timestamp is stored as string)
interface StoredMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: string;
  status?: 'sending' | 'sent' | 'error';
}

interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
}

// Language names for system prompt
const languageNames: Record<string, string> = {
  en: 'English',
  ar: 'Arabic',
  zh: 'Mandarin Chinese',
};

type TabType = 'chat' | 'sandbox';

export default function ChatPage() {
  const { t, locale } = useTranslation();
  const [activeTab, setActiveTab] = useState<TabType>('chat');
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isComposing, setIsComposing] = useState(false);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const shouldAutoScroll = useRef(true);
  const draftSaveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const recognitionRef = useRef<any>(null);

  // Load draft from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedDraft = localStorage.getItem('goblin_chat_draft');
      if (storedDraft) {
        setInputValue(storedDraft);
      }
    }
  }, []);

  // Debounced save of draft to localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      // Clear any pending timeout
      if (draftSaveTimeoutRef.current) {
        clearTimeout(draftSaveTimeoutRef.current);
      }
      // Debounce: save after 500ms of no typing
      draftSaveTimeoutRef.current = setTimeout(() => {
        if (inputValue.trim()) {
          localStorage.setItem('goblin_chat_draft', inputValue);
        } else {
          localStorage.removeItem('goblin_chat_draft');
        }
      }, 500);
    }
    return () => {
      if (draftSaveTimeoutRef.current) {
        clearTimeout(draftSaveTimeoutRef.current);
      }
    };
  }, [inputValue]);

  // Load messages from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedMessages = localStorage.getItem('goblin_chat_messages');
      if (storedMessages) {
        try {
          const parsedMessages = JSON.parse(storedMessages).map((msg: StoredMessage) => ({
            ...msg,
            timestamp: new Date(msg.timestamp)
          }));
          setMessages(parsedMessages);

          const newSession: ChatSession = {
            id: 'session-' + Date.now(),
            title: 'Restored Conversation',
            messages: parsedMessages,
            createdAt: new Date()
          };
          setCurrentSession(newSession);
        } catch (error) {
          console.error('Failed to load stored messages:', error);
          // Fall back to welcome message
          initializeWelcomeMessage();
        }
      } else {
        initializeWelcomeMessage();
      }
    }
  }, []);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (messages.length > 0 && typeof window !== 'undefined') {
      localStorage.setItem('goblin_chat_messages', JSON.stringify(messages));
    }
  }, [messages]);

  // Smart auto-scroll: only scroll if user is near bottom and hasn't scrolled up
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container && shouldAutoScroll.current) {
      const { scrollTop, scrollHeight, clientHeight } = container;
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 50; // 50px threshold
      if (isAtBottom) {
        // Add a small delay to prevent jarring auto-scroll
        setTimeout(() => {
          messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }, 100);
      }
    }
  }, [messages]);

  // Track scroll position to determine if we should auto-scroll
  const handleScroll = () => {
    if (messagesContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = messagesContainerRef.current;
      const isNearBottom = scrollTop + clientHeight >= scrollHeight - 100; // 100px threshold
      const isScrolledUp = scrollTop < scrollHeight - clientHeight - 200; // Show button if scrolled up more than 200px

      shouldAutoScroll.current = isNearBottom;
      setShowScrollButton(isScrolledUp);
    }
  };

  // Keyboard shortcuts handler with proper cleanup
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + K: Focus input
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
      // Ctrl/Cmd + L: Clear chat
      if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
        e.preventDefault();
        clearChat();
      }
      // Escape: Blur input
      if (e.key === 'Escape') {
        inputRef.current?.blur();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Cleanup effect for component unmount
  useEffect(() => {
    return () => {
      // Clear any pending timeouts
      if (draftSaveTimeoutRef.current) {
        clearTimeout(draftSaveTimeoutRef.current);
      }
      // Stop any ongoing speech recognition
      if (recognitionRef.current && recognitionRef.current.stop) {
        try {
          recognitionRef.current.stop();
        } catch (error) {
          console.warn('Failed to stop speech recognition:', error);
        }
      }
    };
  }, []);

  // Scroll to bottom function
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    setShowScrollButton(false);
  };

  const initializeWelcomeMessage = () => {
    const welcomeMessage: Message = {
      id: 'welcome',
      type: 'assistant',
      content: t('chat.welcome'),
      timestamp: new Date(),
      status: 'sent'
    };

    const newSession: ChatSession = {
      id: 'session-' + Date.now(),
      title: t('chat.newConversation'),
      messages: [welcomeMessage],
      createdAt: new Date()
    };

    setMessages([welcomeMessage]);
    setCurrentSession(newSession);
  };

  // Sanitize user input to redact potential PII and secrets before sending to API
  const sanitizeForModel = (text: string): string => {
    let sanitized = text;
    
    // Redact email addresses
    sanitized = sanitized.replace(
      /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
      '[EMAIL_REDACTED]'
    );
    
    // Redact phone numbers (various formats)
    sanitized = sanitized.replace(
      /(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g,
      '[PHONE_REDACTED]'
    );
    
    // Redact SSN-like patterns (XXX-XX-XXXX)
    sanitized = sanitized.replace(
      /\b\d{3}-\d{2}-\d{4}\b/g,
      '[SSN_REDACTED]'
    );
    
    // Redact credit card-like patterns (16 digits with optional separators)
    sanitized = sanitized.replace(
      /\b(?:\d{4}[-\s]?){3}\d{4}\b/g,
      '[CC_REDACTED]'
    );
    
    // Redact API key-like patterns (long alphanumeric strings with specific prefixes)
    sanitized = sanitized.replace(
      /\b(sk-|pk-|api[_-]?key[_-]?|token[_-]?)[a-zA-Z0-9]{20,}\b/gi,
      '[API_KEY_REDACTED]'
    );
    
    // Redact JWT-like patterns
    sanitized = sanitized.replace(
      /\beyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b/g,
      '[JWT_REDACTED]'
    );
    
    return sanitized;
  };

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isTyping) return;

    // Input validation: Check message length (max 1000 characters)
    const trimmedContent = content.trim();
    if (trimmedContent.length > 1000) {
      const errorMessage: Message = {
        id: 'error-' + Date.now(),
        type: 'assistant',
        content: t('chat.errors.tooLong'),
        timestamp: new Date(),
        status: 'error'
      };
      setMessages(prev => [...prev, errorMessage]);
      return;
    }

    // Input validation: Check for potentially harmful content
    if (trimmedContent.length < 2) {
      const errorMessage: Message = {
        id: 'error-' + Date.now(),
        type: 'assistant',
        content: 'Please enter a more meaningful message.',
        timestamp: new Date(),
        status: 'error'
      };
      setMessages(prev => [...prev, errorMessage]);
      return;
    }

    const userMessage: Message = {
      id: 'user-' + Date.now(),
      type: 'user',
      content: content.trim(),
      timestamp: new Date(),
      status: 'sending'
    };

    // Add user message to messages
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    // Clear draft from localStorage on send
    if (typeof window !== 'undefined') {
      localStorage.removeItem('goblin_chat_draft');
    }
    setIsTyping(true);

    try {
      // Use environment variable for API base URL with fallback
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';

      // Get conversation history for context, sanitizing content before sending to API
      const conversationMessages = messages
        .filter(msg => msg.status !== 'error') // Exclude error messages from context
        .map(msg => ({
          role: msg.type === 'user' ? 'user' : 'assistant',
          content: sanitizeForModel(msg.content)
        }));

      // Add the new user message to the conversation (sanitized)
      conversationMessages.push({
        role: 'user',
        content: sanitizeForModel(content.trim())
      });

      // Build system message with language instruction
      const targetLanguage = languageNames[locale] || 'English';
      const systemMessage = locale !== 'en' 
        ? `You are a helpful AI assistant. You MUST respond in ${targetLanguage}. Always use ${targetLanguage} for your responses, regardless of what language the user writes in.`
        : 'You are a helpful AI assistant.';

      // Prepare messages array with system message first
      const messagesWithSystem = [
        { role: 'system', content: systemMessage },
        ...conversationMessages
      ];

      // Send message using same-origin API route (proxied to backend)
      const sendResponse = await fetch(`${apiBaseUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: messagesWithSystem,
          stream: false // Disable streaming - backend returns null with stream:true
        })
      });

      // Check response status and parse error body if needed
      if (!sendResponse.ok) {
        let errorMessage = 'Failed to send message';
        try {
          const errorData = await sendResponse.json();
          if (errorData.error?.message) {
            errorMessage = errorData.error.message;
          } else if (errorData.detail) {
            errorMessage = errorData.detail;
          }
        } catch {
          // If we can't parse error body, use status text
          errorMessage = `Failed to send message: ${sendResponse.status} ${sendResponse.statusText}`;
        }
        throw new Error(errorMessage);
      }

      // Update user message status to 'sent' immediately after successful request
      setMessages(prev => prev.map(m => 
        m.id === userMessage.id ? { ...m, status: 'sent' as const } : m
      ));

      // Check if response is streaming (SSE) or regular JSON
      const contentType = sendResponse.headers.get('content-type') || '';
      const isStreaming = contentType.includes('text/event-stream') || contentType.includes('text/plain');

      if (isStreaming && sendResponse.body) {
        // Handle streaming response
        const assistantMessageId = 'assistant-' + Date.now();
        let streamedContent = '';

        // Create placeholder assistant message for streaming
        const streamingMessage: Message = {
          id: assistantMessageId,
          type: 'assistant',
          content: '',
          timestamp: new Date(),
          status: 'sending'
        };
        setMessages(prev => [...prev, streamingMessage]);

        const reader = sendResponse.body.getReader();
        const decoder = new TextDecoder();

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            
            // Parse SSE format: data: {...}\n\n
            const lines = chunk.split('\n');
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data === '[DONE]') continue;
                
                try {
                  const parsed = JSON.parse(data);
                  // Handle OpenAI-compatible streaming format
                  const delta = parsed.choices?.[0]?.delta?.content || 
                               parsed.content || 
                               parsed.text || 
                               '';
                  if (delta) {
                    streamedContent += delta;
                    // Update the message content incrementally
                    setMessages(prev => prev.map(m => 
                      m.id === assistantMessageId 
                        ? { ...m, content: streamedContent }
                        : m
                    ));
                  }
                } catch {
                  // If not JSON, treat as plain text chunk
                  if (data.trim()) {
                    streamedContent += data;
                    setMessages(prev => prev.map(m => 
                      m.id === assistantMessageId 
                        ? { ...m, content: streamedContent }
                        : m
                    ));
                  }
                }
              } else if (line.trim() && !line.startsWith(':')) {
                // Handle plain text streaming (non-SSE)
                streamedContent += line;
                setMessages(prev => prev.map(m => 
                  m.id === assistantMessageId 
                    ? { ...m, content: streamedContent }
                    : m
                ));
              }
            }
          }
        } finally {
          reader.releaseLock();
        }

        // Mark streaming complete
        setMessages(prev => prev.map(m => 
          m.id === assistantMessageId 
            ? { ...m, status: 'sent' as const, content: streamedContent.trim() || 'No response received.' }
            : m
        ));

      } else {
        // Handle non-streaming JSON response (fallback)
        const responseData = await sendResponse.json();

        // Handle different response formats from the backend
        let assistantContent = '';
        
        // Try Goblin Assistant API format first
        if (responseData.result?.text) {
          assistantContent = responseData.result.text;
        } else if (responseData.result?.response) {
          assistantContent = responseData.result.response;
        } else if (responseData.response) {
          assistantContent = responseData.response;
        } else if (responseData.choices?.[0]?.message?.content) {
          // OpenAI-compatible format
          assistantContent = responseData.choices[0].message.content;
        } else if (responseData.text) {
          assistantContent = responseData.text;
        } else if (responseData.content) {
          assistantContent = responseData.content;
        }
        
        if (!assistantContent || typeof assistantContent !== 'string') {
          console.error('Response format:', responseData);
          throw new Error('Could not parse response from AI');
        }

        // Create assistant message from validated response
        const assistantMessage: Message = {
          id: 'assistant-' + Date.now(),
          type: 'assistant',
          content: assistantContent.trim(),
          timestamp: new Date(),
          status: 'sent'
        };

        setMessages(prev => [...prev, assistantMessage]);
      }

    } catch (error) {
      console.error('Error sending message:', error);

      // Update user message status to 'error'
      setMessages(prev => prev.map(m => 
        m.id === userMessage.id ? { ...m, status: 'error' as const } : m
      ));

      // Map technical errors to user-friendly messages
      let userFriendlyMessage = t('chat.errors.generic');

      if (error instanceof Error) {
        const errorMsg = error.message.toLowerCase();
        console.error('Error details:', error.message);

        if (errorMsg.includes('401') || errorMsg.includes('unauthorized') || errorMsg.includes('api key') || errorMsg.includes('invalid public api key')) {
          userFriendlyMessage = t('chat.errors.auth');
        } else if (errorMsg.includes('403') || errorMsg.includes('forbidden')) {
          userFriendlyMessage = t('chat.errors.forbidden');
        } else if (errorMsg.includes('429') || errorMsg.includes('rate limit')) {
          userFriendlyMessage = t('chat.errors.rateLimit');
        } else if (errorMsg.includes('500') || errorMsg.includes('internal server error')) {
          userFriendlyMessage = t('chat.errors.server');
        } else if (errorMsg.includes('network') || errorMsg.includes('connection') || errorMsg.includes('failed to fetch')) {
          userFriendlyMessage = t('chat.errors.network');
        } else if (errorMsg.includes('timeout')) {
          userFriendlyMessage = t('chat.errors.timeout');
        } else if (errorMsg.includes('could not parse')) {
          userFriendlyMessage = t('chat.errors.parse');
        } else {
          // Show actual error in development for debugging
          userFriendlyMessage = `Error: ${error.message}`;
        }
      }

      // Provide user-friendly error response
      const errorMessage: Message = {
        id: 'error-' + Date.now(),
        type: 'assistant',
        content: userFriendlyMessage,
        timestamp: new Date(),
        status: 'error'
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  const clearChat = () => {
    const welcomeMessage: Message = {
      id: 'welcome',
      type: 'assistant',
      content: t('chat.welcome'),
      timestamp: new Date(),
      status: 'sent'
    };

    setMessages([welcomeMessage]);
    setCurrentSession({
      ...currentSession!,
      messages: [welcomeMessage],
      title: t('chat.newConversation')
    });
  };

  const regenerateResponse = async () => {
    const lastAssistantMessageIndex = messages.map((msg, index) => ({ msg, index }))
      .filter(({ msg }) => msg.type === 'assistant')
      .pop()?.index;

    if (lastAssistantMessageIndex !== undefined) {
      // Find the user message that prompted this response
      const userMessages = messages.slice(0, lastAssistantMessageIndex)
        .filter(msg => msg.type === 'user');

      if (userMessages.length > 0) {
        // Remove the last assistant message
        setMessages(prev => prev.slice(0, lastAssistantMessageIndex));
        setIsTyping(true);

        try {
          // Use environment variable for API base URL with fallback
          const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || '';

          // Get conversation history up to the last user message for context (sanitized)
          const conversationMessages = messages
            .slice(0, lastAssistantMessageIndex)
            .filter(msg => msg.status !== 'error') // Exclude error messages from context
            .map(msg => ({
              role: msg.type === 'user' ? 'user' : 'assistant',
              content: sanitizeForModel(msg.content)
            }));

          // Build system message with language instruction
          const targetLanguage = languageNames[locale] || 'English';
          const systemMessage = locale !== 'en' 
            ? `You are a helpful AI assistant. You MUST respond in ${targetLanguage}. Always use ${targetLanguage} for your responses, regardless of what language the user writes in.`
            : 'You are a helpful AI assistant.';

          // Prepare messages array with system message first
          const messagesWithSystem = [
            { role: 'system', content: systemMessage },
            ...conversationMessages
          ];

          // Send message using Goblin Assistant API
          const sendResponse = await fetch(`${apiBaseUrl}/api/chat`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              messages: messagesWithSystem
            })
          });

          // Check response status and parse error body if needed
          if (!sendResponse.ok) {
            let errorMessage = 'Failed to regenerate response';
            try {
              const errorData = await sendResponse.json();
              if (errorData.error?.message) {
                errorMessage = errorData.error.message;
              } else if (errorData.detail) {
                errorMessage = errorData.detail;
              }
            } catch {
              errorMessage = `Failed to regenerate: ${sendResponse.status} ${sendResponse.statusText}`;
            }
            throw new Error(errorMessage);
          }

          const responseData = await sendResponse.json();

          // Handle different response formats from the backend
          let assistantContent = '';
          
          // Try Goblin Assistant API format first
          if (responseData.result?.text) {
            assistantContent = responseData.result.text;
          } else if (responseData.result?.response) {
            assistantContent = responseData.result.response;
          } else if (responseData.response) {
            assistantContent = responseData.response;
          } else if (responseData.choices?.[0]?.message?.content) {
            // OpenAI-compatible format
            assistantContent = responseData.choices[0].message.content;
          } else if (responseData.text) {
            assistantContent = responseData.text;
          } else if (responseData.content) {
            assistantContent = responseData.content;
          }
          
          if (!assistantContent || typeof assistantContent !== 'string') {
            console.error('Response format:', responseData);
            throw new Error('Could not parse response from AI');
          }

          // Create new assistant message
          const newAssistantMessage: Message = {
            id: 'regenerated-' + Date.now(),
            type: 'assistant',
            content: assistantContent.trim(),
            timestamp: new Date(),
            status: 'sent'
          };

          setMessages(prev => [...prev, newAssistantMessage]);

        } catch (error) {
          console.error('Error regenerating response:', error);

          let userFriendlyMessage = 'Failed to regenerate response. Please try again.';

          if (error instanceof Error) {
            const errorMsg = error.message.toLowerCase();
            if (errorMsg.includes('401') || errorMsg.includes('api key')) {
              userFriendlyMessage = 'Authentication failed during regeneration.';
            } else if (errorMsg.includes('429')) {
              userFriendlyMessage = 'Too many requests. Please wait before regenerating.';
            }
          }

          const errorMessage: Message = {
            id: 'regenerate-error-' + Date.now(),
            type: 'assistant',
            content: userFriendlyMessage,
            timestamp: new Date(),
            status: 'error'
          };

          setMessages(prev => [...prev, errorMessage]);
        } finally {
          setIsTyping(false);
        }
      }
    }
  };

  // Retry a failed user message
  const retryMessage = async (failedMessageId: string) => {
    // Find the user message before the error message
    const errorIndex = messages.findIndex(m => m.id === failedMessageId);
    if (errorIndex === -1) return;

    // Look for the last user message before this error
    let userMessageToRetry: Message | null = null;
    for (let i = errorIndex - 1; i >= 0; i--) {
      if (messages[i].type === 'user') {
        userMessageToRetry = messages[i];
        break;
      }
    }

    if (!userMessageToRetry) return;

    // Remove the error message and retry sending
    setMessages(prev => prev.filter(m => m.id !== failedMessageId));
    
    // Resend the user's original message
    await handleSendMessage(userMessageToRetry.content);
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success('Copied to clipboard!', {
        duration: 2000,
        icon: <CheckCircle className="w-4 h-4" />,
      });
    } catch (err) {
      console.error('Failed to copy text: ', err);
      toast.error('Failed to copy to clipboard', {
        duration: 3000,
        icon: <AlertCircle className="w-4 h-4" />,
      });
    }
  };

  // State for voice input error message
  const [voiceError, setVoiceError] = useState<string | null>(null);

  const handleVoiceInput = async () => {
    // Check for Speech Recognition support (Web Speech API)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const windowAny = window as any;
    const SpeechRecognitionAPI = windowAny.SpeechRecognition || windowAny.webkitSpeechRecognition;

    if (!SpeechRecognitionAPI) {
      setVoiceError('Voice input is not supported in this browser. Please use Chrome, Edge, or Safari.');
      // Clear error after 5 seconds
      setTimeout(() => setVoiceError(null), 5000);
      return;
    }

    // Clear any previous error
    setVoiceError(null);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const recognition = new SpeechRecognitionAPI() as any;
    recognitionRef.current = recognition;

    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsRecording(true);
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setInputValue(prev => prev + (prev ? ' ' : '') + transcript);
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      setIsRecording(false);
      setVoiceError('Speech recognition error. Please try again.');
      setTimeout(() => setVoiceError(null), 5000);
    };

    recognition.onend = () => {
      setIsRecording(false);
    };

    recognition.start();
  };

  // Sanitize HTML content to prevent XSS attacks
  const sanitizeHtml = (html: string): string => {
    // Basic HTML sanitization - remove potentially dangerous tags and attributes
    const dangerousTags = ['script', 'style', 'iframe', 'object', 'embed', 'form', 'input', 'button', 'link', 'meta'];
    const dangerousAttributes = ['onload', 'onerror', 'onclick', 'onmouseover', 'onmouseout', 'onkeydown', 'onkeyup', 'onkeypress'];

    let sanitized = html;

    // Remove dangerous tags
    dangerousTags.forEach(tag => {
      const regex = new RegExp(`<${tag}[^>]*>.*?</${tag}>|<${tag}[^>]*/>`, 'gi');
      sanitized = sanitized.replace(regex, '');
    });

    // Remove dangerous attributes
    dangerousAttributes.forEach(attr => {
      const regex = new RegExp(`\\s${attr}\\s*=\\s*["'][^"']*["']`, 'gi');
      sanitized = sanitized.replace(regex, '');
    });

    return sanitized;
  };

  const formatMessageContent = (content: string) => {
    // Sanitize the content first
    const sanitizedContent = sanitizeHtml(content);

    // Basic code block detection and formatting
    const codeBlockRegex = /```(\w+)?\n?([\s\S]*?)```/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = codeBlockRegex.exec(sanitizedContent)) !== null) {
      // Add text before code block
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: sanitizedContent.slice(lastIndex, match.index)
        });
      }

      // Add code block
      parts.push({
        type: 'code',
        language: match[1] || '',
        content: match[2].trim()
      });

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < sanitizedContent.length) {
      parts.push({
        type: 'text',
        content: sanitizedContent.slice(lastIndex)
      });
    }

    return parts.length > 0 ? parts : [{ type: 'text', content: sanitizedContent }];
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Animated Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-0 w-full h-full">
          <div className="absolute top-20 left-10 w-72 h-72 bg-emerald-500/5 rounded-full blur-3xl animate-pulse"></div>
          <div className="absolute top-40 right-10 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl animate-pulse delay-1000"></div>
          <div className="absolute bottom-20 left-1/3 w-80 h-80 bg-blue-500/5 rounded-full blur-3xl animate-pulse delay-500"></div>
        </div>
      </div>

      {/* Main Content */}
      <div className="relative z-10">
        {/* Header */}
        <header className="border-b border-white/20 bg-gradient-to-r from-white/10 to-white/5 backdrop-blur-sm">
          <div className="container mx-auto px-6 py-4">
            <div className="flex items-center justify-between rtl-preserve">
              <div className="flex items-center space-x-4 rtl:space-x-reverse">
                <div className="w-10 h-10 bg-gradient-to-r from-emerald-500 to-blue-500 rounded-xl flex items-center justify-center shadow-lg shadow-emerald-500/20">
                  <Star className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">{t('home.title')}</h1>
                  <p className="text-slate-400 text-sm">{t('home.subtitle')}</p>
                </div>
              </div>
              
              <div className="flex items-center space-x-2 rtl:space-x-reverse">
                <LanguageSwitcher variant="minimal" />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={clearChat}
                  className="bg-white/10 border-white/30 text-white hover:bg-white/20 font-semibold px-3 py-1.5 rounded-lg transition-all duration-300 backdrop-blur-sm"
                >
                  {t('chat.newChat')}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={regenerateResponse}
                  disabled={isTyping || messages.length === 0}
                  className="bg-white/10 border-white/30 text-white hover:bg-white/20 disabled:bg-white/5 disabled:text-white/50 disabled:border-white/10 font-semibold px-3 py-1.5 rounded-lg transition-all duration-300 backdrop-blur-sm"
                >
                  {t('chat.regenerate')}
                </Button>
              </div>
            </div>
          </div>
        </header>

        {/* Tab Navigation */}
        <nav className="container mx-auto px-6 pt-6">
          <div className="flex space-x-1 bg-white/5 rounded-lg p-1 max-w-md">
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                activeTab === 'chat'
                  ? 'bg-white/20 text-white shadow-lg'
                  : 'text-slate-400 hover:text-white hover:bg-white/10'
              }`}
            >
              <MessageSquare className="w-4 h-4 inline mr-2" />
              Chat
            </button>
            <button
              onClick={() => setActiveTab('sandbox')}
              className={`flex-1 px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                activeTab === 'sandbox'
                  ? 'bg-white/20 text-white shadow-lg'
                  : 'text-slate-400 hover:text-white hover:bg-white/10'
              }`}
            >
              <Code className="w-4 h-4 inline mr-2" />
              Code Sandbox
            </button>
          </div>
        </nav>

        {/* Tab Content */}
        {activeTab === 'chat' ? (
          <>
            {/* Chat Messages */}
            <main className="container mx-auto px-6 py-6 max-w-4xl relative">
          <div
            ref={messagesContainerRef}
            onScroll={handleScroll}
            className="bg-gradient-to-br from-white/10 to-white/5 backdrop-blur-sm border border-white/20 rounded-2xl p-6 shadow-xl max-h-[60vh] overflow-y-auto"
            role="log"
            aria-live="polite"
            aria-atomic="true"
            aria-label="Chat messages"
          >
            <div className="space-y-6">
              {messages.map((message) => {
                const contentParts = formatMessageContent(message.content);
                return (
                  <div
                    key={message.id}
                    className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} group`}
                  >
                    <div className={`flex items-start space-x-3 max-w-xs lg:max-w-2xl ${
                      message.type === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                    }`}>
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                        message.type === 'user'
                          ? 'bg-gradient-to-r from-emerald-500 to-blue-500 shadow-lg shadow-emerald-500/20'
                          : 'bg-gradient-to-r from-purple-500 to-pink-500 shadow-lg shadow-purple-500/20'
                      }`}>
                        {message.type === 'user' ? (
                          <User className="w-4 h-4 text-white" />
                        ) : (
                          <MessageSquare className="w-4 h-4 text-white" />
                        )}
                      </div>

                      <div className={`relative px-4 py-3 rounded-2xl ${
                        message.type === 'user'
                          ? 'bg-gradient-to-r from-emerald-500/20 to-blue-500/20 text-white border border-emerald-500/30'
                          : 'bg-gradient-to-r from-purple-500/20 to-pink-500/20 text-white border border-purple-500/30'
                      }`}>
                        {/* Message Actions */}
                        <div className={`absolute top-2 ${
                          message.type === 'user' ? 'left-2' : 'right-2'
                        } opacity-0 group-hover:opacity-100 transition-opacity duration-200`}>
                          <Button
                            onClick={() => copyToClipboard(message.content)}
                            size="icon"
                            variant="ghost"
                            className="w-6 h-6 hover:bg-white/10 text-slate-400 hover:text-white"
                          >
                            <Copy className="w-3 h-3" />
                          </Button>
                          {message.type === 'assistant' && message.status === 'sent' && (
                            <Button
                              onClick={regenerateResponse}
                              size="icon"
                              variant="ghost"
                              disabled={isTyping}
                              className="w-6 h-6 hover:bg-white/10 text-slate-400 hover:text-white ml-1"
                            >
                              <RotateCcw className="w-3 h-3" />
                            </Button>
                          )}
                        </div>

                        {/* Message Content */}
                        <div className="space-y-2">
                          {contentParts.map((part, index) => (
                            <div key={index}>
                              {part.type === 'text' ? (
                                <p className="text-sm leading-relaxed whitespace-pre-wrap">{part.content}</p>
                              ) : (
                                <div className="bg-slate-800/50 border border-slate-600 rounded-lg p-3 mt-2">
                                  {part.language && (
                                    <div className="text-xs text-slate-400 mb-2 font-mono">
                                      {part.language}
                                    </div>
                                  )}
                                  <pre className="text-sm font-mono text-slate-200 overflow-x-auto">
                                    <code>{part.content}</code>
                                  </pre>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>

                        {/* Message Footer */}
                        <div className="flex items-center justify-between mt-3 pt-2 border-t border-white/10">
                          <span className="text-xs text-slate-400">
                            {message.timestamp.toLocaleTimeString()}
                          </span>
                          <div className="flex items-center space-x-2">
                            {message.status === 'sending' && (
                              <div className="flex items-center space-x-1">
                                <Loader className="w-3 h-3 text-slate-400 animate-spin" />
                                <span className="text-xs text-slate-400">Sending...</span>
                              </div>
                            )}
                            {message.status === 'error' && (
                              <div className="flex items-center space-x-2">
                                <span className="text-xs text-red-400 flex items-center space-x-1">
                                  <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                                  <span>Failed</span>
                                </span>
                                <Button
                                  onClick={() => retryMessage(message.id)}
                                  size="sm"
                                  variant="ghost"
                                  disabled={isTyping}
                                  className="text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10 px-2 py-1 h-auto"
                                >
                                  <RotateCcw className="w-3 h-3 mr-1" />
                                  Retry
                                </Button>
                              </div>
                            )}
                            {message.status === 'sent' && (
                              <span className="text-xs text-green-400 flex items-center space-x-1">
                                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                                <span>Sent</span>
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Typing Indicator */}
              {isTyping && (
                <div className="flex justify-start">
                  <div className="flex items-start space-x-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center">
                      <MessageSquare className="w-4 h-4 text-white" />
                    </div>
                    <div className="bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-white/20 rounded-2xl px-4 py-3">
                      <div className="flex space-x-2">
                        <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce animation-delay-100"></div>
                        <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce animation-delay-200"></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Scroll to Bottom Button */}
          {showScrollButton && (
            <Button
              onClick={scrollToBottom}
              className="absolute bottom-4 right-4 bg-gradient-to-r from-emerald-500 to-blue-500 hover:from-emerald-600 hover:to-blue-600 text-white rounded-full p-3 shadow-lg hover:shadow-xl transition-all duration-300"
              size="icon"
            >
              <ArrowUp className="w-5 h-5" />
            </Button>
          )}
        </main>

        {/* Input Area */}
        <footer className="container mx-auto px-4 sm:px-6 pb-6 sm:pb-8">
          <div className="bg-gradient-to-r from-white/10 to-white/5 backdrop-blur-sm border border-white/20 rounded-2xl p-4 sm:p-6 shadow-xl">
            {/* Voice Error Message */}
            {voiceError && (
              <div className="mb-4 px-4 py-2 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 text-sm">
                {voiceError}
              </div>
            )}

            {/* Multi-line Input Area */}
            <div className="flex items-end space-x-3 sm:space-x-4">
              {/* Voice Input Button */}
              <Button
                onClick={handleVoiceInput}
                disabled={isTyping}
                variant="outline"
                size="icon"
                className={`flex-shrink-0 w-10 h-10 sm:w-12 sm:h-12 rounded-xl border-white/20 ${
                  isRecording
                    ? 'bg-red-500/20 border-red-500/50 text-red-400 animate-pulse'
                    : 'bg-white/5 text-slate-400 hover:bg-white/10 hover:text-white'
                } transition-all duration-200`}
              >
                {isRecording ? '🎙️' : '🎤'}
              </Button>

              {/* Input Field */}
              <div className="flex-1 relative">
                <label htmlFor="chat-input" className="sr-only">Type your message</label>
                <textarea
                  ref={inputRef}
                  id="chat-input"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
                      e.preventDefault();
                      handleSendMessage(inputValue);
                    }
                  }}
                  onCompositionStart={() => setIsComposing(true)}
                  onCompositionEnd={() => setIsComposing(false)}
                  placeholder={t('chat.placeholder')}
                  disabled={isTyping}
                  rows={1}
                  aria-label={t('chat.sendMessage')}
                  aria-describedby="character-count"
                  className="w-full bg-white/10 border border-white/20 text-white placeholder-slate-400 focus:border-emerald-400/50 focus:ring-1 focus:ring-emerald-400/20 rounded-xl px-4 py-3 pr-12 resize-none min-h-[48px] max-h-32 focus:outline-none transition-all duration-200 textarea-auto-height"
                  onInput={(e) => {
                    const target = e.target as EventTarget & HTMLTextAreaElement;
                    target.style.height = 'auto';
                    target.style.height = Math.min(target.scrollHeight, 128) + 'px';
                  }}
                />
                <div className="absolute right-3 bottom-3 flex items-center space-x-2">
                  <Badge
                    id="character-count"
                    variant="outline"
                    className={`text-xs transition-colors ${
                      inputValue.length > 900
                        ? 'bg-yellow-500/20 border-yellow-500/50 text-yellow-400'
                        : inputValue.length > 950
                        ? 'bg-red-500/20 border-red-500/50 text-red-400'
                        : 'bg-white/10 border-white/20 text-slate-400'
                    }`}
                  >
                    {inputValue.length}/1000
                  </Badge>
                </div>
              </div>

              {/* Send Button */}
              <Button
                onClick={() => handleSendMessage(inputValue)}
                disabled={!inputValue.trim() || isTyping}
                className={`flex-shrink-0 w-10 h-10 sm:w-12 sm:h-12 rounded-xl font-semibold transition-all duration-300 ${
                  inputValue.trim() && !isTyping
                    ? 'bg-gradient-to-r from-emerald-500 to-blue-500 hover:from-emerald-600 hover:to-blue-600 text-white shadow-lg hover:shadow-xl hover:shadow-emerald-500/25 transform hover:-translate-y-1 hover:scale-105'
                    : 'bg-slate-600/50 text-slate-400 cursor-not-allowed'
                }`}
                size="icon"
              >
                {isTyping ? (
                  <Loader className="w-5 h-5 sm:w-6 sm:h-6 animate-spin" />
                ) : (
                  <ArrowUp className="w-5 h-5 sm:w-6 sm:h-6" />
                )}
              </Button>
            </div>

            {/* Quick Actions & Status */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between mt-4 pt-4 border-t border-white/20 space-y-3 sm:space-y-0">
              <div className="flex flex-wrap items-center gap-2 text-slate-400 text-sm">
                <Badge variant="outline" className="bg-white/10 border-white/20 text-slate-300 text-xs">
                  Multi-model routing
                </Badge>
                <Badge variant="outline" className="bg-white/10 border-white/20 text-slate-300 text-xs">
                  Privacy first
                </Badge>
                <Badge variant="outline" className="bg-white/10 border-white/20 text-slate-300 text-xs">
                  Real-time responses
                </Badge>
              </div>

              <div className="flex items-center space-x-4 text-xs text-slate-400">
                <span className="hidden sm:inline">
                  {messages.length} messages • Ready to chat
                </span>
                <span className="sm:hidden">
                  {messages.length} msgs
                </span>
                <div className="flex items-center space-x-1">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span>Online</span>
                </div>
              </div>
            </div>

            {/* Keyboard Shortcuts & Mobile Hints */}
            <div className="mt-3 flex flex-col sm:flex-row sm:items-center justify-between space-y-2 sm:space-y-0">
              <div className="hidden sm:flex items-center space-x-4 text-xs text-slate-500">
                <span>⌘K Focus input</span>
                <span>⌘L Clear chat</span>
                <span>Esc Blur input</span>
              </div>
              <div className="sm:hidden">
                <p className="text-xs text-slate-500 text-center">
                  Tap voice button or type your message • Press Enter to send
                </p>
              </div>
            </div>
          </div>
        </footer>
          </>
        ) : (
          /* Sandbox Tab */
          <main className="container mx-auto px-6 py-6 max-w-4xl">
            <Sandbox />
          </main>
        )}

        {/* Toast Notifications */}
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: '#1e1e1e',
              color: '#e0e0e0',
              border: '1px solid #3c3c3c',
            },
          }}
        />
      </div>
    </div>
  );
}
