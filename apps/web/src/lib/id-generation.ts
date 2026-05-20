export const generateClientId = (prefix = 'id'): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
};

export const generateConversationId = (): string => generateClientId('conv');

export const generateMessageId = (): string => generateClientId('msg');