#!/usr/bin/env node

const { execFileSync } = require('node:child_process');
const path = require('node:path');

const repoRoot = path.resolve(__dirname, '..', '..');

const allowlist = [
  'apps/web/src/components/Sparkline.tsx',
  'apps/web/src/components/ThemePreview.tsx',
  'apps/web/src/components/TurnstileWidget.tsx',
  'apps/web/src/features/finance/CorrelationHeatmap.tsx',
  'apps/web/src/features/startup/components/GoblinLoader.tsx',
];

let results = '';

try {
  results = execFileSync(
    'rg',
    ['-n', 'style=\\{\\{', 'apps/web/src', '-g', '*.ts', '-g', '*.tsx', '-g', '*.js', '-g', '*.jsx'],
    {
      cwd: repoRoot,
      encoding: 'utf8',
    },
  ).trim();
} catch (error) {
  if (error.status !== 1) {
    throw error;
  }
}

const violations = results
  .split('\n')
  .filter(Boolean)
  .filter((line) => !allowlist.some((path) => line.startsWith(`${path}:`)));

if (violations.length > 0) {
  console.error('Disallowed inline styles found:');
  console.error(violations.join('\n'));
  process.exit(1);
}

console.log('No disallowed inline styles found.');
