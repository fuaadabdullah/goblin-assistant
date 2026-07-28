export const ANALYTICS_EVENTS = {
  onboarding_started: 'onboarding_started',
  onboarding_step_viewed: 'onboarding_step_viewed',
  onboarding_complete: 'onboarding_complete',
  first_message_sent: 'first_message_sent',
  second_message_sent: 'second_message_sent',
  control_panel_hero_view: 'control_panel_hero_view',
  control_panel_hero_refresh_click: 'control_panel_hero_refresh_click',
  control_panel_hero_action: 'control_panel_hero_action',
} as const;

export const ANALYTICS_STORAGE_KEYS = {
  successful_message_count: 'goblinos-successful-message-count',
} as const;
