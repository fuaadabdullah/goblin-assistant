import { V1_API_PREFIX, postBackend } from './shared';

export const supportMethods = {
  async sendSupportMessage(message: string) {
    return postBackend(`${V1_API_PREFIX}/support/message`, { message });
  },
};
