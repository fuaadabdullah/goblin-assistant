export interface UiErrorPayload {
  code: string;
  userMessage: string;
}

export class UiError extends Error {
  code: string;
  userMessage: string;
  cause?: unknown;

  constructor({ code, userMessage }: UiErrorPayload, cause?: unknown) {
    super(userMessage);
    this.code = code;
    this.userMessage = userMessage;
    this.cause = cause;
  }
}

export const toUiError = (error: unknown, fallback: UiErrorPayload): UiError => {
  if (error instanceof UiError) {
    return error;
  }
  return new UiError(fallback, error);
};
