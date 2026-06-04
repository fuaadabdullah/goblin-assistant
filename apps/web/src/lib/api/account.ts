import { AccountProfile, AccountPreferences, V1_API_PREFIX, putBackend } from './shared';

export const accountMethods = {
  async saveAccountProfile(payload: AccountProfile) {
    return putBackend(`${V1_API_PREFIX}/account/profile`, payload);
  },

  async saveAccountPreferences(payload: AccountPreferences) {
    return putBackend(`${V1_API_PREFIX}/account/preferences`, payload);
  },
};
