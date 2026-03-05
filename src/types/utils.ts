// Shared type utilities to prevent `any` usage

/**
 * Utility type to extract Promise unwrapped type
 */
export type PromiseType<T> = T extends Promise<infer U> ? U : never;

/**
 * Utility type to extract Array element type
 */
export type ArrayType<T> = T extends (infer U)[] ? U : never;

/**
 * Utility type for readonly arrays
 */
export type ReadonlyArrayType<T> = T extends readonly (infer U)[] ? U : never;

/**
 * Utility type for function parameters
 */
export type ParametersType<T extends (...args: any[]) => any> = T extends (...args: infer P) => any ? P : never;

/**
 * Utility type for function return type
 */
export type ReturnTypeType<T extends (...args: any[]) => any> = T extends (...args: any[]) => infer R ? R : never;

/**
 * Utility type for class constructor parameters
 */
export type ConstructorParametersType<T extends new (...args: any[]) => any> = T extends new (...args: infer P) => any ? P : never;

/**
 * Utility type for class instance type
 */
export type InstanceTypeType<T extends new (...args: any[]) => any> = T extends new (...args: any[]) => infer R ? R : never;

/**
 * Non-nullable type
 */
export type NonNullableType<T> = T extends null | undefined ? never : T;

/**
 * Deep readonly type
 */
export type DeepReadonly<T> = {
  readonly [P in keyof T]: T[P] extends object ? DeepReadonly<T[P]> : T[P];
};

/**
 * Deep partial type
 */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

/**
 * Type guard for non-nullable values
 */
export function isNonNullable<T>(value: T): value is NonNullableType<T> {
  return value !== null && value !== undefined;
}

/**
 * Type guard for arrays
 */
export function isArray<T>(value: unknown): value is T[] {
  return Array.isArray(value);
}

/**
 * Type guard for objects
 */
export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Type guard for strings
 */
export function isString(value: unknown): value is string {
  return typeof value === 'string';
}

/**
 * Type guard for numbers
 */
export function isNumber(value: unknown): value is number {
  return typeof value === 'number' && !Number.isNaN(value);
}

/**
 * Type guard for booleans
 */
export function isBoolean(value: unknown): value is boolean {
  return typeof value === 'boolean';
}

/**
 * Type guard for functions
 */
export function isFunction<T extends (...args: any[]) => any>(value: unknown): value is T {
  return typeof value === 'function';
}

/**
 * Type guard for specific shape
 */
export function hasProperty<K extends string>(obj: unknown, key: K): obj is Record<K, unknown> {
  return isObject(obj) && key in obj;
}

/**
 * Safe property access with type narrowing
 */
export function getProperty<T, K extends keyof T>(obj: T, key: K): NonNullableType<T[K]> | undefined {
  if (isObject(obj) && key in obj) {
    const value = obj[key];
    return isNonNullable(value) ? value : undefined;
  }
  return undefined;
}

/**
 * Safe property access with fallback
 */
export function getPropertyWithFallback<T, K extends keyof T>(
  obj: T, 
  key: K, 
  fallback: NonNullableType<T[K]>
): NonNullableType<T[K]> {
  const value = getProperty(obj, key);
  return isNonNullable(value) ? value : fallback;
}

/**
 * Create a type-safe proxy for API responses
 */
export function createApiProxy<T extends Record<string, unknown>>(data: unknown): T | null {
  return isObject(data) ? (data as T) : null;
}

/**
 * Validate and narrow object shape
 */
export function validateShape<T extends Record<string, unknown>>(
  obj: unknown,
  schema: { [K in keyof T]: (value: unknown) => boolean }
): obj is T {
  if (!isObject(obj)) return false;
  
  for (const key in schema) {
    if (!schema[key](obj[key])) {
      return false;
    }
  }
  
  return true;
}

/**
 * Type-safe JSON parsing
 */
export function safeJsonParse<T>(json: string): T | null {
  try {
    return JSON.parse(json) as T;
  } catch {
    return null;
  }
}

/**
 * Union to intersection type helper
 */
export type UnionToIntersection<U> = (U extends any ? (k: U) => void : never) extends (k: infer I) => void ? I : never;

/**
 * Mark properties as optional based on condition
 */
export type ConditionalOptional<T, C> = C extends true ? Partial<T> : T;