export const PACKAGE_NAME = "@goblin/sdk" as const;

export type { paths, components, operations } from "./generated/openapi";
export { createGoblinClient } from "./runtime-client";
