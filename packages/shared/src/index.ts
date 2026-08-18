export type JsonValue =
  | string
  | number
  | boolean
  | null
  | { [key: string]: JsonValue }
  | JsonValue[];

export * from './constants/routes';
export * from './generated/api-proxy-routes';
export * from './constants/providers';
export * from './constants/departments';
