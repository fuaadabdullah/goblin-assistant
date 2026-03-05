'use client';

export const modelService = {
  getAvailableModels: async () => {
    console.log('ModelService.getAvailableModels called');
    // Mock implementation
    return {
      success: true,
      models: [
        {
          id: 'gpt-3.5-turbo',
          name: 'GPT-3.5 Turbo',
          provider: 'openai',
          maxTokens: 4096,
          description: 'Fast and capable model for most tasks',
        },
        {
          id: 'gpt-4',
          name: 'GPT-4',
          provider: 'openai',
          maxTokens: 8192,
          description: 'More powerful model with higher capabilities',
        },
        {
          id: 'claude-3-haiku',
          name: 'Claude 3 Haiku',
          provider: 'anthropic',
          maxTokens: 200000,
          description: 'Anthropic\'s fast and efficient model',
        },
      ],
    };
  },

  getRecommendedModel: async (taskType: 'simple' | 'medium' | 'complex' = 'medium') => {
    console.log('ModelService.getRecommendedModel called with:', taskType);
    // Mock implementation
    const recommendations: Record<string, string> = {
      simple: 'gpt-3.5-turbo',
      medium: 'gpt-4',
      complex: 'claude-3-haiku',
    };

    return {
      success: true,
      modelId: recommendations[taskType] || 'gpt-3.5-turbo',
    };
  },

  getModelStatus: async (modelId: string) => {
    console.log('ModelService.getModelStatus called with:', modelId);
    // Mock implementation
    return {
      success: true,
      status: 'available',
      lastUsed: new Date().toISOString(),
      usageCount: Math.floor(Math.random() * 100),
    };
  },
};
