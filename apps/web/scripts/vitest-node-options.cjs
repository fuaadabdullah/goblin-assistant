#!/usr/bin/env node
// Print NODE_OPTIONS for the vitest scripts.
//
// Node 22+ ships an experimental global `localStorage` that shadows jsdom's,
// so tests disable it with --no-experimental-webstorage. Node 20 (the CI and
// .nvmrc version) does not know that flag and refuses to start when it is in
// NODE_OPTIONS, so only emit it where the runtime accepts it.
const flag = '--no-experimental-webstorage';
const existing = process.env.NODE_OPTIONS || '';
const options = process.allowedNodeEnvironmentFlags.has(flag)
  ? `${existing} ${flag}`.trim()
  : existing;
process.stdout.write(options);
