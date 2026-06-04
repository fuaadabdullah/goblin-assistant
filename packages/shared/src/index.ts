export type JsonValue =
  | string
  | number
  | boolean
  | null
  | { [key: string]: JsonValue }
  | JsonValue[];

export interface ApiSuccessEnvelope<T> {
  success: true;
  data: T;
}

export interface ApiErrorPayload {
  code: string;
  type: string;
  message: string;
  request_id?: string;
  timestamp?: string;
  trace_id?: string;
  details?: Record<string, JsonValue>;
}

export interface ApiErrorEnvelope {
  success: false;
  error: ApiErrorPayload;
}

export type ApiEnvelope<T> = ApiSuccessEnvelope<T> | ApiErrorEnvelope;
