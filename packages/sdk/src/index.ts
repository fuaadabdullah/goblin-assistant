export const PACKAGE_NAME = "@goblin/sdk" as const;

export type { components, $defs } from "./generated/components";
export type { operations } from "./generated/operations";
export type { paths, webhooks } from "./generated/paths";
export { createGoblinClient } from "./runtime-client";
