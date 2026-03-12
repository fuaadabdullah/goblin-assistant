'use client';

import { apiClient } from '@/lib/api';
import type { AccountPreferences } from '@/lib/api';

type PreferencesResponse = AccountPreferences & { theme?: string; defaultModel?: string; highContrast?: boolean; fontSize?: string };

export const databaseService = {
  logUsage: async (
    _userId: string,
    provider: string,
    model: string,
    tokens: number,
    cost: number,
    latency: number,
  ) => {
    try {
      await apiClient.saveAccountPreferences({ provider, model, tokens, cost, latency } as AccountPreferences);
    } catch {
      // Non-blocking — usage logging must not break the caller
    }
    return { success: true, logId: `${Date.now().toString(36)}` };
  },

  getUserPreferences: async (_userId: string) => {
    try {
      const prefs = (await (apiClient as any).getAccountPreferences?.() ??
        fetch('/account/preferences', { credentials: 'include' }).then((r) => r.ok ? r.json() : null)) as PreferencesResponse | null;
      return {
        success: true,
        preferences: {
          theme: prefs?.theme ?? 'default',
          defaultModel: prefs?.default_model ?? prefs?.defaultModel ?? '',
          highContrast: Boolean((prefs as any)?.high_contrast ?? prefs?.highContrast ?? false),
          fontSize: (prefs as any)?.font_size ?? prefs?.fontSize ?? 'medium',
        },
      };
    } catch {
      return {
        success: true,
        preferences: { theme: 'default', defaultModel: '', highContrast: false, fontSize: 'medium' },
      };
    }
  },

  saveUserPreferences: async (_userId: string, preferences: AccountPreferences) => {
    await apiClient.saveAccountPreferences(preferences);
    return { success: true };
  },

  getConversationHistory: async (_userId: string, limit = 10) => {
    const conversations = await apiClient.listConversations();
    return {
      success: true,
      conversations: conversations.slice(0, limit).map((c) => ({
        id: c.conversationId,
        title: c.title,
        createdAt: c.createdAt,
        messageCount: c.messageCount,
      })),
    };
  },
};
