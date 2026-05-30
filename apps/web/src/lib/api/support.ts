import { postBackend } from './shared';

export const supportMethods = {
  async sendSupportMessage(message: string) {
    return postBackend('/support/message', { message });
  },
};
