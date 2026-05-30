import { AccountProfile, AccountPreferences, putBackend } from './shared';

export const accountMethods = {
  async saveAccountProfile(payload: AccountProfile) {
    return putBackend('/account/profile', payload);
  },

  async saveAccountPreferences(payload: AccountPreferences) {
    return putBackend('/account/preferences', payload);
  },
};
