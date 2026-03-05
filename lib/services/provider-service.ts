'use client';

export const providerService = {
  getProviders: async () => {
    console.log('ProviderService.getProviders called');
    // Mock implementation
    return [
      {
        id: 'openai',
        name: 'OpenAI',
        description: 'OpenAI language models',
        isAvailable: true,
        type: 'openai',
        costConfig: {
          inputCostPerToken: 0.000001,
          outputCostPerToken: 0.000002,
        },
        models: [
          {
            id: 'gpt-3.5-turbo',
            name: 'GPT-3.5 Turbo',
            providerId: 'openai',
            maxTokens: 4096,
            description: 'Fast and capable model',
            isAvailable: true,
          },
          {
            id: 'gpt-4',
            name: 'GPT-4',
            providerId: 'openai',
            maxTokens: 8192,
            description: 'More powerful model',
            isAvailable: true,
          },
        ],
      },
      {
        id: 'anthropic',
        name: 'Anthropic',
        description: 'Anthropic language models',
        isAvailable: true,
        type: 'anthropic',
        costConfig: {
          inputCostPerToken: 0.0000015,
          outputCostPerToken: 0.000003,
        },
        models: [
          {
            id: 'claude-3-haiku',
            name: 'Claude 3 Haiku',
            providerId: 'anthropic',
            maxTokens: 200000,
            description: 'Fast and efficient model',
            isAvailable: true,
          },
        ],
      },
    ];
  },

  getProviderHealth: async () => {
    console.log('ProviderService.getProviderHealth called');
    // Mock implementation
    return {
      openai: { status: 'healthy', lastChecked: new Date().toISOString() },
      anthropic: { status: 'healthy', lastChecked: new Date().toISOString() },
    };
  },

  getProviderStatus: async (providerId: string) => {
    console.log('ProviderService.getProviderStatus called with:', providerId);
    // Mock implementation
    return {
      status: 'available',
      lastChecked: new Date().toISOString(),
      responseTime: Math.floor(Math.random() * 100) + 50,
    };
  },
};
