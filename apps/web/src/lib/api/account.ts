import {
  AccountProfile,
  AccountPreferences,
  V1_API_PREFIX,
  getBackend,
  putBackend,
} from './shared';

export const accountMethods = {
  async getAccountProfile() {
    return getBackend<AccountProfile>(`${V1_API_PREFIX}/account/profile`);
  },

  async saveAccountProfile(payload: AccountProfile) {
    return putBackend(`${V1_API_PREFIX}/account/profile`, payload);
  },

  async getAccountPreferences() {
    return getBackend<Record<string, unknown>>(`${V1_API_PREFIX}/account/preferences`);
  },

  async saveAccountPreferences(payload: AccountPreferences) {
    return putBackend(`${V1_API_PREFIX}/account/preferences`, payload);
  },
};
