import React, { useState, useEffect, useRef } from 'react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { runtimeClient, runtimeClientDemo } from '../api/api-client';
import { Send, Bot, User, DollarSign, Zap, MessageSquare } from 'lucide-react';
import { useToast } from '../contexts/ToastContext';
import { useProvider } from '../contexts/ProviderContext';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  cost?: number;
  tokens?: number;
  provider?: string;
  model?: string;
}

interface ChatInterfaceProps {
  demoMode?: boolean;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ demoMode = false }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [providers, setProviders] = useState<string[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [totalCost, setTotalCost] = useState(0);
  const [totalTokens, setTotalTokens] = useState(0);
  const [loadingProviders, setLoadingProviders] = useState(true);
  const [loadingModels, setLoadingModels] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { showError } = useToast();
  const { selectedProvider, setSelectedProvider, selectedModel, setSelectedModel } = useProvider();

  // Get the appropriate runtime client
  const getRuntimeClient = () => (demoMode ? runtimeClientDemo : runtimeClient);

  // Load providers on mount
  useEffect(() => {
    const loadProviders = async () => {
      try {
        setLoadingProviders(true);
        const client = getRuntimeClient();
        const providerList = await client.getProviders();
        setProviders(providerList);
        if (providerList.length > 0 && !selectedProvider) {
          setSelectedProvider(providerList[0]);
        }
      } catch (error) {
        console.error('Failed to load providers:', error);
        showError(
          'Failed to Load Providers',
          'Unable to connect to the server. Please check your connection and try again.'
        );
      } finally {
        setLoadingProviders(false);
      }
    };
    loadProviders();
  }, [demoMode, selectedProvider, setSelectedProvider, showError]);

  // Load models when provider changes
  useEffect(() => {
    const loadModels = async () => {
      if (!selectedProvider) return;

      try {
        setLoadingModels(true);
        const client = getRuntimeClient();
        const modelList = await client.getProviderModels(selectedProvider);
        setModels(modelList);
        if (modelList.length > 0 && !selectedModel) {
          setSelectedModel(modelList[0]);
        }
      } catch (error) {
        console.error('Failed to load models:', error);
        showError(
          'Failed to Load Models',
          `Unable to load models for ${selectedProvider}. Please try selecting a different provider.`
        );
      } finally {
        setLoadingModels(false);
      }
    };
    loadModels();
  }, [selectedProvider, selectedModel, setSelectedModel, demoMode, showError]);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const client = getRuntimeClient();

      // For chat, we'll use a simple orchestration that just calls one goblin
      // const orchestration = `docs-writer: ${inputMessage.trim()}`;

      let responseContent = '';
      let messageCost = 0;
      let messageTokens = 0;

      await client.executeTaskStreaming(
        'docs-writer',
        inputMessage.trim(),
        chunk => {
          if (chunk.chunk) {
            responseContent += chunk.chunk;
          }
          if (typeof chunk.cost_delta === 'number') {
            messageCost += chunk.cost_delta;
          }
          if (typeof chunk.token_count === 'number') {
            messageTokens += chunk.token_count;
          }
        },
        response => {
          if (typeof response.cost === 'number') messageCost = response.cost;
          if (response.model)
            messageTokens =
              response.model === 'demo-model'
                ? Math.floor(responseContent.length / 4)
                : messageTokens;
        },
        undefined, // code
        selectedProvider,
        selectedModel
      );

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: responseContent,
        timestamp: new Date(),
        cost: messageCost,
        tokens: messageTokens,
        provider: selectedProvider,
        model: selectedModel,
      };

      setMessages(prev => [...prev, assistantMessage]);
      setTotalCost(prev => prev + messageCost);
      setTotalTokens(prev => prev + messageTokens);
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
      showError('Message Failed', errorMessage);
      const errorMessageObj: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Sorry, I encountered an error: ${errorMessage}. Please try again.`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessageObj]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatCost = (cost: number) => `$${cost.toFixed(4)}`;
  const formatTokens = (tokens: number) => tokens.toLocaleString();

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header with Provider/Model Selection */}
        <div className="bg-white border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-semibold text-gray-900 flex items-center">
                <MessageSquare className="w-6 h-6 mr-2 text-blue-600" />
                Goblin Assistant
              </h1>
              <div className="flex items-center space-x-2">
                <Select
                  value={selectedProvider}
                  onValueChange={setSelectedProvider}
                  disabled={loadingProviders}
                >
                  <SelectTrigger className="w-32">
                    <SelectValue placeholder={loadingProviders ? 'Loading...' : 'Provider'} />
                  </SelectTrigger>
                  <SelectContent>
                    {providers.map(provider => (
                      <SelectItem key={provider} value={provider}>
                        {provider}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select
                  value={selectedModel}
                  onValueChange={setSelectedModel}
                  disabled={loadingModels || !selectedProvider}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder={loadingModels ? 'Loading...' : 'Model'} />
                  </SelectTrigger>
                  <SelectContent>
                    {models.map(model => (
                      <SelectItem key={model} value={model}>
                        {model}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Cost/Tokens Display */}
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-1 text-sm text-gray-600">
                <DollarSign className="w-4 h-4" />
                <span>{formatCost(totalCost)}</span>
              </div>
              <div className="flex items-center space-x-1 text-sm text-gray-600">
                <Zap className="w-4 h-4" />
                <span>{formatTokens(totalTokens)}</span>
              </div>

              {demoMode && (
                <Badge variant="secondary" className="text-xs">
                  Demo Mode
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 mt-8">
              <Bot className="w-12 h-12 mx-auto mb-4 text-gray-400" />
              <h3 className="text-lg font-medium mb-2">Welcome to Goblin Assistant!</h3>
              <p>Start a conversation by typing a message below.</p>
            </div>
          )}

          {messages.map(message => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white border border-gray-200 text-gray-900'
                }`}
              >
                <div className="flex items-center mb-1">
                  {message.role === 'user' ? (
                    <User className="w-4 h-4 mr-1" />
                  ) : (
                    <Bot className="w-4 h-4 mr-1" />
                  )}
                  <span className="text-xs opacity-75">
                    {message.timestamp.toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                {message.role === 'assistant' && message.cost && (
                  <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-200 text-xs opacity-75">
                    <span>
                      {message.provider} • {message.model}
                    </span>
                    <div className="flex items-center space-x-2">
                      <span>{formatCost(message.cost)}</span>
                      <span>{formatTokens(message.tokens || 0)} tokens</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-gray-200 px-4 py-2 rounded-lg">
                <div className="flex items-center space-x-2">
                  <Bot className="w-4 h-4" />
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.1s]"></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.2s]"></div>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="bg-white border-t border-gray-200 p-4">
          <div className="flex space-x-2">
            <Input
              ref={inputRef}
              value={inputMessage}
              onChange={e => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              disabled={isLoading}
              className="flex-1"
            />
            <Button
              onClick={handleSendMessage}
              disabled={!inputMessage.trim() || isLoading}
              className="px-4"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
          <div className="text-xs text-gray-500 mt-2">
            Press Enter to send, Shift+Enter for new line
          </div>
        </div>
      </div>

      {/* Sidebar with Stats */}
      <div className="w-80 bg-white border-l border-gray-200 p-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center">
              <DollarSign className="w-5 h-5 mr-2" />
              Session Stats
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Total Cost</span>
              <span className="font-semibold text-green-600">{formatCost(totalCost)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Total Tokens</span>
              <span className="font-semibold">{formatTokens(totalTokens)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Messages</span>
              <span className="font-semibold">{messages.length}</span>
            </div>

            {messages.length > 0 && (
              <>
                <hr className="my-4" />
                <div>
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Recent Messages</h4>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {messages.slice(-3).map(message => (
                      <div key={message.id} className="text-xs text-gray-600">
                        <div className="flex items-center space-x-1">
                          {message.role === 'user' ? (
                            <User className="w-3 h-3" />
                          ) : (
                            <Bot className="w-3 h-3" />
                          )}
                          <span className="truncate flex-1">
                            {message.content.substring(0, 30)}...
                          </span>
                          {message.cost && (
                            <span className="text-green-600">{formatCost(message.cost)}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
