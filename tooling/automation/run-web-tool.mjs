#!/usr/bin/env node

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const tool = process.argv[2];
const args = process.argv.slice(3);
if (!tool || !/^[a-z0-9_-]+$/i.test(tool)) {
  console.error('Usage: run-web-tool.mjs <tool> [...args]');
  process.exit(2);
}

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const tmpDir = path.join(repoRoot, '.tmp');
const playwrightBrowsers = path.join(repoRoot, '.playwright', 'browsers');
fs.mkdirSync(tmpDir, { recursive: true });
fs.mkdirSync(path.join(repoRoot, 'apps', 'web', 'coverage', '.tmp'), { recursive: true });
fs.mkdirSync(playwrightBrowsers, { recursive: true });

const executable = process.platform === 'win32' ? `${tool}.cmd` : tool;
const result = spawnSync(executable, args, {
  cwd: process.cwd(),
  env: {
    ...process.env,
    TMPDIR: tmpDir,
    PLAYWRIGHT_BROWSERS_PATH: playwrightBrowsers,
  },
  shell: process.platform === 'win32',
  stdio: 'inherit',
  windowsHide: true,
});

if (result.error) {
  console.error(`Unable to run ${tool}: ${result.error.message}`);
  process.exit(1);
}
process.exit(result.status ?? 1);
