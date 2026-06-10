#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');

const repoRoot = path.resolve(__dirname, '..', '..');
const scanRoot = path.join(repoRoot, 'apps', 'web', 'src');
const EXTS = new Set(['.ts', '.tsx', '.js', '.jsx']);
const PATTERN = /style=\{\{/;

const allowlist = [
  'apps/web/src/components/Sparkline.tsx',
  'apps/web/src/components/ThemePreview.tsx',
  'apps/web/src/components/TurnstileWidget.tsx',
  'apps/web/src/features/finance/CorrelationHeatmap.tsx',
  'apps/web/src/features/startup/components/GoblinLoader.tsx',
];

function collectFiles(dir) {
  const results = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...collectFiles(full));
    } else if (EXTS.has(path.extname(entry.name))) {
      results.push(full);
    }
  }
  return results;
}

const violations = [];

for (const file of collectFiles(scanRoot)) {
  const rel = path.relative(repoRoot, file).replace(/\\/g, '/');
  if (allowlist.some((p) => rel === p)) continue;

  const lines = fs.readFileSync(file, 'utf8').split('\n');
  for (let i = 0; i < lines.length; i++) {
    if (PATTERN.test(lines[i])) {
      violations.push(`${rel}:${i + 1}: ${lines[i].trim()}`);
    }
  }
}

if (violations.length > 0) {
  console.error('Disallowed inline styles found:');
  console.error(violations.join('\n'));
  process.exit(1);
}

console.log('No disallowed inline styles found.');
