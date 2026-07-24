import { AccountProfile, AccountPreferences, getFrontend, putFrontend } from './shared';

const INTERNAL_ACCOUNT_PREFIX = '/api/account';

export const accountMethods = {
  async getAccountProfile() {
    return getFrontend<AccountProfile>(`${INTERNAL_ACCOUNT_PREFIX}/profile`);
  },

  async saveAccountProfile(payload: AccountProfile) {
    return putFrontend(`${INTERNAL_ACCOUNT_PREFIX}/profile`, payload);
  },

  async getAccountPreferences() {
    return getFrontend<Record<string, unknown>>(`${INTERNAL_ACCOUNT_PREFIX}/preferences`);
  },

  async saveAccountPreferences(payload: AccountPreferences) {
    return putFrontend(`${INTERNAL_ACCOUNT_PREFIX}/preferences`, payload);
  },
};
